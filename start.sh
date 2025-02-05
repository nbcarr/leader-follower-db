#!/bin/bash

python3 db.py --role leader --port 8000 --peers 8001 8002 &
sleep 1
python3 db.py --role follower --port 8001 --peers 8000 8002 &
sleep 1
python3 db.py --role follower --port 8002 --peers 8001 8002 &
wait