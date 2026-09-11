#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0
playwright install chromium
