#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt
unset PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD
playwright install chromium
