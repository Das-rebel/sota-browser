#!/bin/bash
# Use Chrome's existing browser via CDP instead of launching a fresh one
export CHROME_CDP_URL=$(curl -s http://localhost:60807/json/version 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('webSocketDebuggerUrl',''))" 2>/dev/null)
if [ -z "$CHROME_CDP_URL" ]; then
    echo "Error: Chrome CDP not available. Is Chrome running with remote debugging?"
    exit 1
fi
echo "Using Chrome CDP: ${CHROME_CDP_URL:0:60}..."
pi "$@"
