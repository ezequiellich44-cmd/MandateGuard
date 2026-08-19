#!/usr/bin/env bash
# Publish mandateguard to PyPI.
#
# 1. Create an API token at https://pypi.org/manage/account/token/
# 2. Export it:  export TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-...
# 3. Run this script.
set -euo pipefail

cd "$(dirname "$0")/.."

python -m pip install --quiet --upgrade build twine
python -m build
python -m twine upload --non-interactive dist/*
echo "Published. https://pypi.org/project/mandateguard/"
