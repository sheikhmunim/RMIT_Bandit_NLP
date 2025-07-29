#!/bin/bash

# Define the remote server and destination path
REMOTE_USER="pal"
REMOTE_HOST="bandit"
REMOTE_PATH="/home/pal/bandit_nlp"

# Copy the entire bandit-movement-controller directory excluding build, devel, and TiagoMovementController.jpeg
rsync -av --exclude='build' --exclude='devel' bandit_nlp "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH"