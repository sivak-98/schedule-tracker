#!/bin/bash
echo "Building the application"
compose_command="docker compose up -d"
echo "Executing command: $compose_command"
sudo $compose_command
exit_code=$?

if [ $exit_code -ne 0 ]; then
    echo "Docker Build Failed with: $exit_code"
else
    echo "Docker build succeeded."
fi