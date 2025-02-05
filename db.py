# TOOO:
# - error handling/retries when replicating
# - test persistence on crash
# - separate this out into logical modules (api, routes, Node, etc)
# - Additional node metrics (read/write latency, replication stats, etc)
# - UI for metrics

import argparse
import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional

import aiofiles
import httpx
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # For UI
    allow_methods=["*"],
    allow_headers=["*"],
)


class WriteRequest(BaseModel):
    key: str
    value: str


class LeaderInfoRequest(BaseModel):
    is_leader: bool
    leader_port: int


class Node:
    def __init__(self, is_leader: bool, port: int, peer_ports: List[int]):
        self.leader_port = min(peer_ports) if not is_leader else port
        self.is_leader = is_leader
        self.port = port
        self.peer_ports = peer_ports
        self.db = "db.json"
        self.wal = "wal.log"
        self.data: Dict = self.load()
        self.alive_peers = set()
        self.endpoint = "http://localhost"

        # Node Metrics
        self.start_time = int(time.time())
        self.last_leader_time = int(time.time()) if is_leader else None
        self.writes = 0
        self.reads = 0

    def load(self):
        data = {}
        try:
            with open(self.db, mode="r") as f:
                data = json.loads(f.read())
        except FileNotFoundError:
            logging.info(f"No DB file found ({self.db}). Starting empty")

        try:
            with open(self.wal, mode="r") as f:
                for line in f.readlines():
                    op = json.loads(line)
                    if op["type"] == "write":
                        data[op["key"]] = op["value"]
        except FileNotFoundError:
            pass
        except Exception as e:
            logging.fatal(f"Could not load data from WAL ({self.wal})")

        return data

    async def replicate_to_followers(self, peer: int, request: WriteRequest):
        logging.info(f"Starting replicate from {self.port}...")
        async with httpx.AsyncClient() as client:
            try:
                url = f"{self.endpoint}:{peer}/replicate"
                await client.post(
                    url, json={"key": request.key, "value": request.value}
                )
            except Exception as e:
                logging.error(f"Failed to replicate to {peer}: {e}")

    async def heartbeat(self):
        while True:
            await asyncio.sleep(5)
            for peer in self.peer_ports:
                try:
                    async with httpx.AsyncClient() as client:
                        await client.get(f"{self.endpoint}:{peer}/health")
                        logging.info(f"Heartbeat success for peer {peer}")
                        self.alive_peers.add(peer)
                except Exception as e:
                    logging.error(f"Heartbeat failed for peer {peer}: {e}")
                    if peer in self.alive_peers:
                        self.alive_peers.remove(peer)

    async def check_leader_health(self):
        while True:
            await asyncio.sleep(10)
            try:
                async with httpx.AsyncClient() as client:
                    await client.get(f"{self.endpoint}:{self.leader_port}/health")
            except Exception as e:
                logging.error(f"Heartbeat failed for Leader ({self.leader_port}): {e}")
                await self.start_election()

    async def start_election(self):
        # https://www.educative.io/answers/what-is-a-bully-election-algorithm
        logging.info(f"Port {self.port} starting election")
        higher_ports = [p for p in self.peer_ports if p > self.port]

        highest_port = None
        # Find highest port that is active
        for port in higher_ports:
            try:
                async with httpx.AsyncClient() as client:
                    port_health = await client.get(f"{self.endpoint}:{port}/health")
                    if port_health.status_code == 200:
                        highest_port = port
            except Exception as e:
                logging.error(f"Failed to check port: {port}: {e}")
                continue

        # Set the current port as new leader - either no other ports are active, or this is the highest one available
        if not highest_port:
            logging.info(f"Electing {self.port} as new leader")
            self.is_leader = True
            self.leader_port = self.port
            self.last_leader_time = int(time.time())
            for peer in self.peer_ports:
                await self.notify_new_leader(
                    peer, self.port, False
                )  # Notify everyone else about the new leader
        else:  # Otherwise, elect the highest port as new leader
            logging.info(f"Electing {highest_port} as new leader")
            self.is_leader = False
            self.leader_port = highest_port
            await self.notify_new_leader(
                highest_port, highest_port, True
            )  # Assign highest_port as new leader and notify it
            for peer in self.peer_ports:
                if peer != highest_port:
                    await self.notify_new_leader(
                        peer, highest_port, False
                    )  # Notify everyone else about the new leader

    async def notify_new_leader(self, peer: int, leader_port: int, is_leader: bool):
        async with httpx.AsyncClient() as client:
            try:
                await client.post(
                    f"{self.endpoint}:{peer}/new_leader",
                    json={"leader_port": leader_port, "is_leader": is_leader},
                )
                logging.info(f"Notified {peer} about new leader {leader_port}")
            except Exception as e:
                logging.fatal(f"Failed to notify peer of new leader {peer}: {e}")

    async def write(self, request: WriteRequest):
        logging.info(
            f"Node {self.port} RECEIVED write request: (k: {request.key}, v: {request.value})"
        )
        if not self.is_leader:
            logging.info(f"Node: {self.port} is not leader - cannot write")
            return False

        await self.update_wal(
            {"type": "write", "key": request.key, "value": request.value}
        )
        self.data[request.key] = request.value
        self.writes += 1
        for peer in self.alive_peers:
            await self.replicate_to_followers(peer, request)
        logging.info(
            f"Node {self.port} COMPLETED write request: (k: {request.key}, v: {request.value})"
        )
        return True

    async def read(self, key):
        logging.info(f"Node {self.port} RECEIVED read request: (k: {key})")
        self.reads += 1
        if key not in self.data:
            return False
        logging.info(f"Node {self.port} COMPLETED read request: (k: {key})")
        return self.data[key]

    async def update_wal(self, op):
        logging.info(f"Node {self.port} updating WAL...")
        timestamp = int(time.time())
        op["timestamp"] = timestamp
        async with aiofiles.open(self.wal, mode="a") as f:
            try:
                await f.write(f"{json.dumps(op)}\n")
            except Exception as e:
                logging.fatal(f"Could not append to WAL: {e}")

    async def persist(self):
        logging.info(f"Node {self.port} persisting data...")
        while True:
            await asyncio.sleep(60)
            try:
                async with aiofiles.open("db.json", mode="w") as f:
                    await f.write(json.dumps(self.data))
                try:
                    os.remove(self.wal)
                except FileNotFoundError:
                    pass
            except Exception as e:
                logging.error(f"Could not persist data: {e}")

    async def metrics(self):
        uptime = int(time.time()) - self.start_time
        leadership_time = (
            int(time.time()) - self.last_leader_time if self.last_leader_time else 0
        )

        try:
            wal_size = os.path.getsize(self.wal)
        except FileNotFoundError:
            wal_size = 0

        return {
            "node": {
                "id": self.port,
                "role": "leader" if self.is_leader else "follower",
                "uptime_seconds": uptime,
                "status": "healthy",
            },
            "peers": {
                "total": len(self.peer_ports),
                "alive": len(self.alive_peers),
                "ports": list(self.peer_ports),
            },
            "writes": {
                "total": self.writes,
            },
            "reads": {
                "total": self.reads,
            },
            "leadership": {
                "leader_port": self.leader_port,
                "time_as_leader_seconds": leadership_time,
            },
            "storage": {"keys_count": len(self.data), "wal_size_bytes": wal_size},
        }

    async def dump(self):
        return self.data


# Global node instance
node: Optional[Node] = None


@app.on_event("startup")
async def startup_event():
    if node.is_leader:
        asyncio.create_task(node.heartbeat())
    else:
        asyncio.create_task(node.check_leader_health())
    asyncio.create_task(node.persist())


@app.post("/write")
async def write(request: WriteRequest):
    ok = await node.write(request)
    return ok


@app.get("/read/{key}")
async def read(key: str):
    val = await node.read(key)
    return val


@app.post("/replicate")
async def replicate(request: WriteRequest):
    node.data[request.key] = request.value
    return True


@app.get("/health")
async def health():
    return {"status": "alive", "is_leader": node.is_leader}


@app.get("/metrics")
async def metrics():
    return await node.metrics()


@app.get("/dump")
async def dump():
    return await node.dump()


@app.post("/new_leader")
async def new_leader(leader_info: LeaderInfoRequest):
    node.is_leader = leader_info.is_leader
    node.leader_port = leader_info.leader_port
    if node.is_leader:
        node.last_leader_time = int(time.time())
        asyncio.create_task(node.heartbeat())
    return {"status": "updated"}


@app.websocket("/ws/logs/{port}")
async def websocket_endpoint(websocket: WebSocket, port: int):
    await websocket.accept()
    log_file = f"node_{port}.log"

    async def watch_logs():
        async with aiofiles.open(log_file, mode="r") as f:
            await f.seek(0, 2)
            while True:
                line = await f.readline()
                if line:
                    await websocket.send_text(line)
                await asyncio.sleep(0.1)

    try:
        await watch_logs()
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=["leader", "follower"], required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument(
        "--peers", type=int, nargs="+", help="Ports of peer nodes", required=True
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(f"node_{args.port}.log"),
            logging.StreamHandler(),
        ],
    )

    node = Node(
        is_leader=(args.role == "leader"), port=args.port, peer_ports=args.peers
    )

    uvicorn.run(app, host="localhost", port=args.port)
