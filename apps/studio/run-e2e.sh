#!/bin/bash
# Run E2E tests in Docker
# Usage: ./run-e2e.sh [playwright args]

# Build the image properly first
docker compose -f docker-compose.e2e.yaml build

# Run the tests
# --rm removes the container after exit
docker compose -f docker-compose.e2e.yaml run --rm e2e npx playwright test "$@"
