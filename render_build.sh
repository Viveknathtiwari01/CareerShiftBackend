#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Install Chromium next to the Playwright package so the same path works at
# build and runtime on Render (must also set PLAYWRIGHT_BROWSERS_PATH=0 at runtime;
# main.py / html_to_pdf do this automatically).
export PLAYWRIGHT_BROWSERS_PATH=0
unset PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD

# OS libs first when apt is available (Render native builds usually allow this).
if python -m playwright install-deps chromium; then
  echo "Playwright system dependencies installed"
else
  echo "WARNING: playwright install-deps failed; continuing with browser download only"
fi

python -m playwright install chromium

echo "Playwright Chromium install complete (PLAYWRIGHT_BROWSERS_PATH=0)"
