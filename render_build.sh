#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt
export PLAYWRIGHT_BROWSERS_PATH=0
unset PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD
python -m playwright install chromium
