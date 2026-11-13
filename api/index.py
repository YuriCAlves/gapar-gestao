"""Entrada Serverless da Vercel: expoe a aplicacao Flask (WSGI) para /api/* e /auth/*."""
import os
import sys
from pathlib import Path

# Garante que o pacote `app` (raiz do repositorio) seja importavel no runtime da Vercel.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# O sistema de arquivos da Vercel e somente leitura, exceto /tmp.
if os.getenv("VERCEL"):
    os.environ.setdefault("UPLOAD_FOLDER", "/tmp/uploads")

from app import create_app  # noqa: E402

app = create_app(os.getenv("FLASK_ENV", "production"))
