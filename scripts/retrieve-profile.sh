#!/bin/bash
set -a
source .env
set +a

# Download the profile JSON file from the remote server
scp "$SSH_USER@$SSH_HOST:/root/ProjectEulerBot/profiles/authentic.json" profiles/
