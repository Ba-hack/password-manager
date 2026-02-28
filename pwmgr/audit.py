from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .models import Entry, VaultData


@dataclass
class WeakFinding:
    entry: Entry
    reasons: List[str]


def _fingerprint_password(pw: str) -> str:
    """
    Empreinte non réversible (hash). Sert uniquement à détecter la réutilisation.
    """
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


def _char_classes(pw: str) -> int:
    has_lower = any(c.islower() for c in pw)
    has_upper = any(c.isupper() for c in pw)
    has_digit = any(c.isdigit() for c in pw)
    has_symbol = any((not c.isalnum()) for c in pw)
    return sum([has_lower, has_upper, has_digit, has_symbol])


def audit_vault(data: VaultData, min_length: int = 12) -> Tuple[List[WeakFinding], Dict[str, List[Entry]]]:
    """
    Retourne:
      - weak: liste des entrées avec mdp faible (règles simples)
      - reused: dict fingerprint -> [entries] (seulement ceux réutilisés)
    """
    weak: List[WeakFinding] = []

    # 1) Faibles
    for e in data.entries.values():
        reasons: List[str] = []
        pw = e.password or ""
        if len(pw) < min_length:
            reasons.append(f"length<{min_length}")
        if _char_classes(pw) < 3:
            reasons.append("not_enough_char_classes(<3)")
        if reasons:
            weak.append(WeakFinding(entry=e, reasons=reasons))

    # 2) Réutilisés
    buckets: Dict[str, List[Entry]] = {}
    for e in data.entries.values():
        fp = _fingerprint_password(e.password or "")
        buckets.setdefault(fp, []).append(e)

    reused = {fp: ents for fp, ents in buckets.items() if len(ents) >= 2}

    return weak, reused