#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────
# TalentAI — AI Resume Screening System
# One-command setup script
# Run:  bash setup.sh
# ──────────────────────────────────────────────────────────────────
set -e

PYTHON=${PYTHON:-python3}
VENV=".venv"

echo ""
echo "═══════════════════════════════════════════════"
echo "   TalentAI Resume Screener — Setup"
echo "═══════════════════════════════════════════════"
echo ""

# 1. Virtual environment
if [ ! -d "$VENV" ]; then
  echo "[1/6] Creating virtual environment..."
  $PYTHON -m venv $VENV
else
  echo "[1/6] Virtual environment already exists."
fi

# Activate
source $VENV/bin/activate 2>/dev/null || source $VENV/Scripts/activate

# 2. Pip install
echo "[2/6] Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "      ✓ Dependencies installed"

# 3. NLTK data
echo "[3/6] Downloading NLTK language data..."
python -c "
import nltk
for pkg in ['stopwords', 'wordnet', 'punkt', 'punkt_tab', 'averaged_perceptron_tagger']:
    try:
        nltk.download(pkg, quiet=True)
    except Exception as e:
        print(f'  Warning: could not download {pkg}: {e}')
print('  ✓ NLTK data ready')
"

# 4. Database
echo "[4/6] Running database migrations..."
python manage.py migrate --run-syncdb -q
echo "      ✓ Database ready (db.sqlite3)"

# 5. Create media directory
echo "[5/6] Creating media directory..."
mkdir -p media/resumes
echo "      ✓ media/resumes/ ready"

# 6. Superuser
echo "[6/6] Create your admin account:"
python manage.py createsuperuser

echo ""
echo "═══════════════════════════════════════════════"
echo "   ✅  Setup complete!"
echo "═══════════════════════════════════════════════"
echo ""
echo "  Start the server:"
echo "    source .venv/bin/activate"
echo "    python manage.py runserver"
echo ""
echo "  Then open:  http://127.0.0.1:8000/"
echo "  Admin:      http://127.0.0.1:8000/admin/"
echo ""
