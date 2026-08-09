#!/bin/sh
# The one and only way tests are run. CI calls this same script, so a green
# run here means a green run there.
set -e
exec python3 -m pytest tests/ "$@"
