#!/bin/zsh
source ~/.zshrc
set -e

cd /home/james/src/james_notes/

git pull
git add -A
git commit -m 'updates'
git push
