#!/bin/bash
set -euo pipefail

PORT="${1:-9222}"
PROFILE_DIR="${TMPDIR:-/tmp}/keycrm-devtools-profile"

# Close regular Chrome instances to ensure flags are applied to a fresh process.
osascript -e 'tell application "Google Chrome" to quit' >/dev/null 2>&1 || true
sleep 1

open -na "Google Chrome" --args \
  --remote-debugging-port="$PORT" \
  --user-data-dir="$PROFILE_DIR"

echo "Chrome launched with remote debugging on: http://127.0.0.1:${PORT}"
echo "Verify in browser: http://127.0.0.1:${PORT}/json/version"
