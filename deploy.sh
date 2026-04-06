#!/bin/bash

set -e  # стоп при ошибке

echo "📥 Pulling latest code..."
git pull

echo "🐳 Stopping old containers..."
docker compose down

echo "🔨 Building new image..."
docker compose build

echo "🚀 Starting containers..."
docker compose up -d

echo "🧹 Cleaning unused images..."
docker image prune -f

echo "✅ Deploy completed successfully!"

