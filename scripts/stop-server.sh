#!/bin/bash
set -a
source .env
set +a

# Kill any running eulerbot.py process on the remote server
ssh "$SSH_USER@$SSH_HOST" "systemctl stop eulerbot.service"
