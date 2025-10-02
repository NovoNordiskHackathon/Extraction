#!/bin/bash
# conversion_run.sh
# Simple script: convert and rename output to match input basename

# Check argument
if [ -z "$1" ]; then
  echo "Usage: $0 <input_document>"
  exit 1
fi

# Resolve paths
INPUT_DOC="$(realpath "$1" 2>/dev/null)"
if [ ! -f "$INPUT_DOC" ]; then
  echo "Error: File not found: $1"
  exit 1
fi

# Paths and names
INPUT_DIR="$(dirname "$INPUT_DOC")"
INPUT_BASE="$(basename "$INPUT_DOC" | sed 's/\.[^.]*$//')"
TEMP_OUTPUT="$INPUT_DIR/output_document.pdf"
FINAL_OUTPUT="$INPUT_DIR/${INPUT_BASE}.pdf"

# Set Adobe creds and SSL bypass
export PDF_SERVICES_CLIENT_ID="aa40bdd8077047138b178685e7b5136e"
export PDF_SERVICES_CLIENT_SECRET="p8e-k4Y6mGmZsjbn9EMzxEt-ga0Bwwhc1Y55"
export PYTHONHTTPSVERIFY=0

# Activate venv if exists
PROJECT_ROOT="/home/ibab/PycharmProjects/Extraction"
VENV_PATH="/home/ibab/PycharmProjects/DL-Lab/.venv"
[ -f "$VENV_PATH/bin/activate" ] && source "$VENV_PATH/bin/activate"

# Run conversion
python3 "$PROJECT_ROOT/acrobattools/API_calls/doc_to_pdf.py" \
  "$INPUT_DOC" \
  "$TEMP_OUTPUT"

# Rename if conversion succeeded
if [ $? -eq 0 ] && [ -f "$TEMP_OUTPUT" ]; then
  mv "$TEMP_OUTPUT" "$FINAL_OUTPUT"
  echo "Conversion successful: $FINAL_OUTPUT"
  exit 0
else
  echo "Conversion failed."
  exit 1
fi

