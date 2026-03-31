#!/bin/bash
set -a
source .env
set +a

# Ensure remote directory exists
ssh "$SSH_USER@$SSH_HOST" "mkdir -p /root/ProjectEulerBot/scripts"

# Upload all files in the local scripts/ folder to the remote scripts/ folder
scp scripts/* "$SSH_USER@$SSH_HOST:/root/ProjectEulerBot/scripts/"
