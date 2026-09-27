#!/usr/bin/env bash
# Bundle the viewer: renders/src/main.js + three.js (renders/build/node_modules) -> renders/viewer.bundle.js
# (IIFE, runs from file:// with no network).  The esbuild command is defined once, as the "build" script
# of package.json (also used by CI).  First time only: (cd renders/build && npm ci)  — installs the exact
# versions pinned in package-lock.json (esbuild, three, playwright-core for the headless tests).
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x node_modules/.bin/esbuild ]; then
  echo "build.sh: $(pwd)/node_modules is missing or incomplete; run 'npm ci' in $(pwd) first" >&2
  exit 1
fi
npm run --silent build
echo "built ../viewer.bundle.js ($(du -h ../viewer.bundle.js | cut -f1))"
