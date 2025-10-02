#!/bin/bash
# run_extraction.sh
# Bash script to set env variables and run extraction in one go

# Absolute path to project root
PROJECT_DIR="/home/ibab/PycharmProjects/Extraction"

# Set environment variables
export PDF_SERVICES_CLIENT_ID="aa40bdd8077047138b178685e7b5136e"
export PDF_SERVICES_CLIENT_SECRET="p8e-k4Y6mGmZsjbn9EMzxEt-ga0Bwwhc1Y55"

# Activate virtual environment (optional if already active)
source "$PROJECT_DIR/.venv/bin/activate"

# Run the Python extraction script
python3 "$PROJECT_DIR/acrobattools/API_calls/simpletext_extract.py" \
    "$PROJECT_DIR/Data/Data/Protocol_REF.pdf"
