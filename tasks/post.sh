#!/bin/bash
export PATH="/home/james/miniconda3/bin:$PATH"
cd ~/src/Work\ Notes/
curl "192.168.0.32/string/?input1=$(python tasks.py |sed 's/\- \[ \] //g' |sed 's/ *📅 */ /g' | jq --slurp --raw-input --raw-output @uri)" 
