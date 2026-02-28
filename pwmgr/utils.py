from __future__ import annotations

import secrets
import string
import threading
import time
from typing import Optional, List

import pyperclip


def normalize_tags(tags: Optional[str]) -> List[str]:
    """
    Convertit une string "mail,work, perso" -> ["mail","work","perso"]
    """
    if not tags:
        return []
    return [t.strip() for t in tags.split(",") if t.strip()]


def generate_password(length: int = 20, with_symbols: bool = True) -> str:
    """
    Génère un mot de passe aléatoire.
    - secrets.choice => RNG cryptographique
    """
    if length < 8:
        raise ValueError("length must be >= 8")

    alphabet = string.ascii_letters + string.digits
    if with_symbols:
        alphabet += "!@#$%^&*()-_=+[]{};:,.?/"

    return "".join(secrets.choice(alphabet) for _ in range(length))


def copy_to_clipboard_autoclear(secret_value: str, seconds: int = 20) -> None:
    """
    Copie secret_value dans le presse-papiers puis efface après N secondes,
    MAIS uniquement si le presse-papiers n'a pas changé entre temps.
    (évite d'effacer un autre truc que tu as copié après)
    """
    pyperclip.copy(secret_value)

    def worker(expected: str, delay: int):
        time.sleep(delay)
        try:
            current = pyperclip.paste()
            if current == expected:
                pyperclip.copy("")
        except Exception:
            # En cas de problème d'accès au clipboard, on ignore l'effacement.
            pass

    t = threading.Thread(target=worker, args=(secret_value, seconds), daemon=True)
    t.start()