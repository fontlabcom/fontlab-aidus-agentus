#!/bin/sh
# this_file: test.sh
# Full suite with coverage in the Python 3.13+ brain environment, then the
# host-side subset (no AI dependencies) on Python 3.11 like FontLab's own.
# Extra arguments go to the brain run only, e.g. ./test.sh -x -k config
set -eu
cd "$(dirname "$0")"
BRAIN=${AIDUS_TEST_PYTHON:-.venv/bin/python}
HOST=${AIDUS_HOST_PYTHON:-.venv-host/bin/python}
for py in "$BRAIN" "$HOST"; do
  if [ ! -x "$py" ]; then
    echo "test.sh: $py missing; see README.md 'Develop and test'" >&2
    exit 2
  fi
done
"$BRAIN" -m pytest --import-mode=importlib -p no:cacheprovider --cov --cov-report=term "$@"
"$HOST" -m pytest --import-mode=importlib -p no:cacheprovider -q \
  tests --ignore=tests/core --ignore=tests/test_production_entrypoint.py \
  --ignore-glob='tests/test_brain_*'
