#!/bin/bash
VENV_DIR=".venv"

usage() {
  cat <<EOF
Usage: $0 [-c config-file] [-v venv-dir]

Options:
  -v DIR    Path to virtual environment directory (overrides VENV_DIR env)
  -h        Show this help
EOF
}

# Parse optional CLI args: -c <config>
while getopts ":c:v:h" opt; do
  case "${opt}" in
    v)
      VENV_DIR="${OPTARG}"
      ;;
    h)
      usage
      exit 0
      ;;
    \?)
      echo "Invalid option: -${OPTARG}" >&2
      usage
      exit 1
      ;;
    :) 
      echo "Option -${OPTARG} requires an argument." >&2
      usage
      exit 1
      ;;
  esac
done


if [ ! -d "${VENV_DIR}" ]; then
  python3.11 -m venv "${VENV_DIR}"
fi
source "${VENV_DIR}/bin/activate"

if [ -f "requirements.txt" ]; then
  pip install --upgrade pip setuptools wheel
  pip install -r requirements.txt
else
  echo "requirements.txt not found" >&2
fi

if [ -f "setup.py" ] || [ -f "pyproject.toml" ]; then
  pip install -e .
else
  echo "setup.py or pyproject.toml not found — cannot install package in editable mode." >&2
fi