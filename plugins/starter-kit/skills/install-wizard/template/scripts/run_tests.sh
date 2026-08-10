#!/bin/sh
# The one and only way tests are run. CI calls this same script, so a green
# run here means a green run there — this is also why the glossary and
# CI-superset checks live here instead of as extra steps bolted onto the
# workflow file: anything CI runs that this script does not is exactly the
# "green locally, red in CI, no way to reproduce it" case the superset
# check exists to catch. Only pytest takes "$@" (e.g. --maxfail=1 from the
# Stop hook); the other two take no arguments.
set -e
"${PYTHON:-python3}" -m pytest tests/ "$@"
"${PYTHON:-python3}" scripts/check_glossary.py
"${PYTHON:-python3}" scripts/check_ci_superset.py
