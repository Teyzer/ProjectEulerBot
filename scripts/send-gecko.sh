#!/bin/bash
set -a
source .env
set +a

# Upload the database to the remote server
scp geckodriver "$SSH_USER@[$SSH_HOST]:/usr/local/bin/"
