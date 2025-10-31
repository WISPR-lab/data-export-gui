if [ ! -d "${VENV_DIR}" ]; then
  python3.11 -m venv "${VENV_DIR}"
fi
source "${VENV_DIR}/bin/activate"

if [ -f "requirements.txt" ]; then
  pip install --upgrade pip setuptools wheel
  pip install -r requirements.txt
else
  echo "requirements.txt not found — try 'pip install -e .' if you have setup.py/pyproject." >&2
fi