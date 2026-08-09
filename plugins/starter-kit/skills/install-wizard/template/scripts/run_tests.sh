#!/bin/sh
# The one and only way tests are run. CI calls this same script, so a green
# run here means a green run there.
set -e
exec "${PYTHON:-python3}" -m pytest tests/ "$@"
