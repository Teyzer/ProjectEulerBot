#!/bin/bash
set -a
source .env
set +a

# Download the database from the remote server
scp "$SSH_USER@[$SSH_HOST]:/root/ProjectEulerBot/databases/authentic.db" databases/
