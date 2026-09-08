#!/bin/bash
set -euo pipefail
cd /workspace/najd-planting-monitor
/usr/bin/npm install
/usr/bin/npm run build
echo BUILD_OK
