# Distributed Leader-Follower Database

Persistent distributed database implementation with leader-follower replication and automatic leader election, and a front-end dashboard to interact and monitor the nodes

For front-end demo, click [here](https://github.com/nbcarr/leader-follower-db/blob/main/README.md#ui-demo)

## Back-End Overview (Python)
- [Leader-follower architecture](https://www.educative.io/answers/leader-and-follower-replication) for data replication
- [Bully algorithm](https://www.educative.io/answers/what-is-a-bully-election-algorithm) for leader election
- [Write-ahead logging (WAL)](https://www.educative.io/answers/what-is-the-write-ahead-log) for durability 
- REST API endpoints using [FastAPI](https://fastapi.tiangolo.com/)
- WebSocket integration for log streaming

## Front-End Overview (React/JavaScript)
The front-end allows for interacting with the database:
- Add/remove nodes dynamically
- Read/write values
- View node metrics/cluster status
- Monitor node logs in real time
- Track leader election/node health
- Visualize replication across nodes

![Screenshot 2025-02-05 at 8 11 16 PM](https://github.com/user-attachments/assets/af6ccfd4-2e8d-4cb5-ba8a-7595bb52b6bc)


## Back-End Architecture

The database consists of multiple nodes where one acts as a leader (accepting writes) and others as followers 

The leader handles all write operations and replicates data to followers. 

If the leader fails, remaining nodes elect a new leader using the Bully algorithm.

The in-memory data is ocassionally written out on-disk for persistence, and recovers from crashes using the WAL

### Components
- `controller.py`: Dynamically manages node lifecycle and cluster coordination
- `db.py`: Core component managing state, replication, and leader election
- **WAL**: Write-ahead log for crash recovery/durability
- **REST API**: FastAPI endpoints for reads/writes and node operations
- **WebSockets**: Real time log streaming


## How to Use

### Prerequisites
```bash
pip3 install requirements.txt
npm install # for UI dependencies
```

### Controller
The controller manages the lifecycle and coordination of all nodes in the cluster (see `controller.py`), and is the main entry point of the system. It keeps track of the active nodes with an in-memory hashmap of `port` -> `pid`, and uses this to start/kill nodes with API endpoints (with FastAPI).

To run the controller:
```bash
python3 controller.py
```

The controller exposes a few endpoints that the front end uses for adding/removing nodes. This might get out of date, but when you run `controller.py`, you can visit `http://<url>:<port>/docs` to view dynamically generated API endpoints
- `GET /nodes`: Returns a list of active nodes, including the `port` and `pid`
- `POST /nodes/start`: Starts a node with a `role` (leader/follower) on a `port` with a list of `peers`
- `POST /nodes/kill`: Kills a node on a specific `port`

Starting a node launches a new process and invokes the `db.py` module (which implements the `Node` class). It will look something like this, depending on the arguments:
```
python3 db.py --role leader --port 8000 --peers 8001
```

### Database
The database module (`db.py`) implements the distributed `Node` class with:
- Leader-follower replication
- Leader election
- WAL
- Health monitoring

You can skip running `controller.py`, and launch the `db.py` module directly as separate processes/terminals:

```bash
python3 db.py --role leader --port 8000 --peers 8001
python3 db.py --role follower --port 8001 --peers 8000
```

There are a few API endpoints that `db.py` exposes (again, you can visit `http://<url>:<port>/docs` to view dynamically generated API endpoints)

Public:
- `POST /write` - Write key-value pair
- `GET /read/{key}` - Read value by key
- `GET /metrics` - Node metrics
- `GET /health` - Node health status

Internal:
- `POST /replicate` - Node replication
- `POST /new_leader` - Leader election
- `POST /new_peer` - Peer addition notification
- `POST /remove_peer` - Peer removal notification
- `ws/logs/{port}` - Real-time log streaming

### Running the UI
Once the cluster is running (either from `controller.py` or `db.py`), the UI can be started:

```bash
cd metrics-ui
npm run dev
```

### UI Demo

- Dynamically adding/removing nodes through `Controller`, and demonstrating new leader election:

https://github.com/user-attachments/assets/074d1468-2ed3-4e86-8886-98b677dffd01

- Select a node to get access to the logs:

https://github.com/user-attachments/assets/ba3fcc40-c259-4cb2-b34b-97bca055169e

- Use the checkbox to show data available on each node, demonstrating replication and logs (the follower node also receives the new value):

https://github.com/user-attachments/assets/13667c04-4ce8-4d0f-8f02-6a171cdd5b1a

- Scale up to as many nodes as you'd like:

https://github.com/user-attachments/assets/62794d1c-6d07-4d09-b691-775a7de663d3


