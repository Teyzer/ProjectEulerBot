#!/bin/bash
set -a
source .env
set +a

# Upload the database to the remote server
scp databases/authentic.db "$SSH_USER@$SSH_HOST:/root/ProjectEulerBot/databases/"
