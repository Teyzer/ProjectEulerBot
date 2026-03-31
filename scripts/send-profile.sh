#!/bin/bash
set -a
source .env
set +a

# Upload the profile JSON file to the remote server
scp profiles/authentic.json "$SSH_USER@$SSH_HOST:/root/ProjectEulerBot/profiles/"
