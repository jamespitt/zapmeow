#!/bin/zsh
source ~/.zshrc
set -e

cd /home/james/src/james_notes/tasks

eval "python $1" >> "$2" 2>&1
