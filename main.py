# main.py
from fastapi import FastAPI
import uvicorn
import argparse
from pydantic import BaseModel
from typing import Dict, List, Optional
import asyncio
import httpx
import logging
import aiofiles
import json
import time
import os

app = FastAPI()

class WriteRequest(BaseModel):
    key: str
    value: str

class Node:
    def __init__(self, is_leader: bool, port: int, peer_ports: List[int]):
        self.leader_port = min(peer_ports) if not is_leader else port
        self.is_leader = is_leader
        self.port = port
        self.peer_ports = peer_ports
        self.data: Dict = self.load()
        self.alive_peers = set()
    
    def load(self):
        data = {}
        try:
            with open('db.json', mode='r') as f:
                data = json.loads(f.read())
        except FileNotFoundError:
            print("No DB file found. Starting empty")
                
        try:
            with open('wal.log', mode='r') as f:
                for line in f.readlines():
                    op = json.loads(line)
                    if op['type'] == "write":
                        data[op["key"]] = op["value"]
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"FATAL: Could not load data from WAL")
        
        return data
                
        
    async def replicate_to_followers(self, peer: int, request: WriteRequest):
        async with httpx.AsyncClient() as client:
            try:
                url = f"http://localhost:{peer}/replicate"
                await client.post(url, json={"key": request.key, "value": request.value})
            except Exception as e:
                print(f"Failed to replicate to {peer}: {e}") 

    async def heartbeat(self):
        while True:
            await asyncio.sleep(15)
            for peer in self.peer_ports:
                try:
                    async with httpx.AsyncClient() as client:
                        await client.get(f"http://localhost:{peer}/health")
                        print(f"Heartbeat success for peer {peer}")
                        self.alive_peers.add(peer)
                except Exception as e:
                    print(f"Heartbeat failed for peer {peer}: {e}")
                    self.alive_peers.remove(peer)
                    
    async def check_leader_health(self):
        while True:
            await asyncio.sleep(15)
            try:
                async with httpx.AsyncClient() as client:
                    await client.get(f"http://localhost:{self.leader_port}/health")
            except Exception:
                print(f"Heartbeat failed for Leader ({self.leader_port})")
                await self.start_election()
                
    async def start_election(self):
        if self.port == max(self.peer_ports):
            self.is_leader = True
            for peer in self.peer_ports:
                await self.notify_new_leader(peer)
                
    async def notify_new_leader(self, peer: int):
        async with httpx.AsyncClient() as client:
            try:
                url = f"http://localhost:{peer}/new_leader"
                await client.post(url, json={"leader_port": self.port})
            except Exception as e: # This is fatal
                print(f"Failed to notify peer of new leader {peer}: {e}") 
        
    async def write(self, request: WriteRequest):
        if not self.is_leader:
            print(f"Node: {self.port} is not leader - cannot write")
            return False

        await self.update_wal({"type": "write", "key": request.key, "value": request.value})
        self.data[request.key] = request.value
        for peer in self.alive_peers: #TODO: error handling/retries
            await self.replicate_to_followers(peer, request)
        return True
    
    async def read(self, key):
        if key not in self.data:
            return False
        return self.data[key]
    
    async def update_wal(self, op):
        timestamp = int(time.time())
        op["timestamp"] = timestamp
        async with aiofiles.open('wal.log', mode='a') as f:
            try:
                await f.write(f"{json.dumps(op)}\n")
            except Exception as e:
                print(f"FATAL: Could not append to WAL: {e}")
    
    async def persist(self):
        while True:
            await asyncio.sleep(60)
            try:
                async with aiofiles.open('db.json', mode='w') as f:
                    await f.write(json.dumps(self.data))
                try:
                    os.remove('wal.log')
                except FileNotFoundError:
                    pass
            except Exception as e:
                print(f"ERROR: Could not persist data: {e}")

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
    return {"status": "alive"}

@app.post("/new_leader")
async def new_leader(leader_info: dict):
    node.is_leader = False
    node.leader_port = leader_info["leader_port"]
    return {"status": "updated"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=["leader", "follower"], required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--peers", type=int, nargs="+", help="Ports of peer nodes", required=True)
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    node = Node(
        is_leader=(args.role == "leader"),
        port=args.port,
        peer_ports=args.peers
    )
    
    uvicorn.run(app, host="localhost", port=args.port)