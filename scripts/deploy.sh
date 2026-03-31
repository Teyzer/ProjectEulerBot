#!/bin/bash
set -a
source .env
set +a

# Pull latest changes from the repo
ssh "$SSH_USER@$SSH_HOST" "cd ProjectEulerBot && git pull"

# Restart the bot
./scripts/restart.sh
