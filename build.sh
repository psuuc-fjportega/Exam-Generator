#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Building React frontend..."
cd frontend
npm install
npm run build
cd ..

echo "==> Running database migrations..."
alembic upgrade head

echo "==> Build complete!"
