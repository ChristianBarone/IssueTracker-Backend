#!/usr/bin/env bash
# Sortir si hi ha errors
set -o errexit

# Instal·lar dependències de Python
pip install -r requirements.txt

# Entrar a la carpeta on hi ha el manage.py
cd src

# Recollir fitxers estàtics i aplicar migracions a la base de dades
python manage.py collectstatic --no-input
python manage.py migrate --fake-initial # No tira errors si les taules ja existeixen