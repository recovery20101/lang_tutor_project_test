#!/bin/sh
echo "Running npm install..."
npm install
echo "Starting Next.js dev server..."
npm run dev -- -H 0.0.0.0