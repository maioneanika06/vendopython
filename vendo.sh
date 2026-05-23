#!/bin/bash

echo "starting vendo system"

source venv/bin/activate

python printer_worker.py &
sleep 0.5

python left.py &
python right.py &

wait
