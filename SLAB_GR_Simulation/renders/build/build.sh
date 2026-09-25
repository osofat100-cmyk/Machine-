#!/usr/bin/env bash
# Bundle the viewer (three.js is vendored in renders/build/node_modules).  Output: renders/viewer.bundle.js
set -euo pipefail
cd "$(dirname "$0")"
NODE_PATH="$(pwd)/node_modules" ./node_modules/.bin/esbuild ../src/main.js --bundle --format=iife --target=es2020 --outfile=../viewer.bundle.js --log-level=warning
echo "built ../viewer.bundle.js ($(du -h ../viewer.bundle.js | cut -f1))"
