#!/bin/bash



echo "starting vendo system"



source venv/bin/activate



python left.py &



python right.py &



wait
