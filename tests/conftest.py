"""
pytest charge automatiquement conftest.py.

Ici on ajoute la racine du projet au sys.path, pour que:
  from pwmgr.crypto import ...
fonctionne même si le package n'est pas installé via pip.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .../password-manager
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))