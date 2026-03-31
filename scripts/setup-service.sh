#!/bin/bash
set -a
source .env
set +a

# Define the path to your local service file
SERVICE_FILE="scripts/eulerbot.service"

echo "Uploading service file to server..."
# Because you are root, you can write directly to /etc/systemd/system
scp "$SERVICE_FILE" "$SSH_USER@[$SSH_HOST]:/etc/systemd/system/eulerbot.service"

echo "Configuring and starting the service..."
ssh "$SSH_USER@$SSH_HOST" "
    echo 'Reloading systemd daemon...'
    systemctl daemon-reload
    
    echo 'Enabling and starting eulerbot...'
    systemctl enable --now eulerbot.service
    
    echo 'Current status:'
    systemctl status eulerbot.service --no-pager
"

echo "Service setup complete!"