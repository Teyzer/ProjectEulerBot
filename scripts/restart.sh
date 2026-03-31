#!/bin/bash
set -a
source .env
set +a

ssh "$SSH_USER@$SSH_HOST" 'systemctl restart eulerbot.service'
