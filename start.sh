#!/bin/bash
# Startup script for FutureOracle
# This script activates the virtual environment and starts the Streamlit app

set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -f "venv/bin/activate" ]]; then
  echo "venv/ not found. Create it first (example): python -m venv venv"
  exit 1
fi

source venv/bin/activate
streamlit run src/app.py --server.port 8501
