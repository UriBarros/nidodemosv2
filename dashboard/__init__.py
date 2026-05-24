"""Dashboard package — carrega .env antes de qualquer import filho."""

from pathlib import Path

from dotenv import load_dotenv

# Carrega .env da raiz do projeto (E:\gtrifood\.env)
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_PROJECT_ROOT / ".env")
