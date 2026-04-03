#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Installing Python Dependencies..."
pip install -r backend/requirements.txt

echo "Installing Node Dependencies..."
cd frontend
npm install

echo "Building Frontend..."
npm run build
cd ..

echo "Build Configuration Complete."
# h
