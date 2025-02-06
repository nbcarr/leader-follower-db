import logging
import os
import signal
import subprocess
from typing import List, Optional
import requests

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


class NodeStartRequest(BaseModel):
    role: str
    port: int
    peers: List[int]


class NodeKillRequest(BaseModel):
    port: int


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # For UI
    allow_methods=["*"],
    allow_headers=["*"],
)

PORT = 8080


class Controller:
    def __init__(self):
        # Port -> PID
        self.active_nodes = {}

    def list_nodes(self):
        return {
            "nodes": [
                {"port": port, "pid": pid} for port, pid in self.active_nodes.items()
            ]
        }

    def start_node(self, role: str, port: int, peers: List[int]):
        logging.info(f"Requested to start {port} with role {role} and peers {peers}")
        cmd = f"python3 db.py --role {role} --port {port} --peers {' '.join(map(str, peers))}"
        process = subprocess.Popen(cmd.split())
        self.active_nodes[port] = process.pid
        logging.info(f"Successfully started node on port {port} (pid: {process.pid})")

        for peer_port in peers:
            try:
                requests.post(
                    f"http://localhost:{peer_port}/new_peer",
                    json={"new_peer_port": port},
                )
            except Exception as e:
                logging.error(f"Failed to notify {peer_port} about new node: {e}")

        return {"status": "started", "port": port, "pid": process.pid}

    def kill_node(self, port):
        logging.info("Requested to kill node on port {port}")
        pid = self.active_nodes.get(port)
        if not pid:
            logging.warning(f"Node on port {port} does not exist")
            return {"status": "failed", "msg": f"Port {port} does not exist"}
        os.kill(pid, signal.SIGTERM)
        self.active_nodes.pop(port)
        logging.info("Successfully killed node on port {port} (pid: {pid})")
        return {"status": "killed", "port": port, "pid": pid}


@app.post("/nodes/start")
async def start_node(request: NodeStartRequest):
    return controller.start_node(request.role, request.port, request.peers)


@app.post("/nodes/kill")
async def kill_node(request: NodeKillRequest):
    return controller.kill_node(request.port)


@app.get("/nodes")
async def list_nodes():
    return controller.list_nodes()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(f"controller.log"),
            logging.StreamHandler(),
        ],
    )

    controller = Controller()
    logging.info(f"Starting controller on port {PORT}...")
    uvicorn.run(app, host="localhost", port=PORT)
