from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from .crypto import encrypt_json, decrypt_json, KdfParams
from .models import VaultData


DEFAULT_VAULT_PATH = Path.home() / ".pwmgr_vault.json"


class Vault:
    """Gestion du fichier vault sur disque (chiffré)."""

    def __init__(self, path: Path):
        self.path = path

    def exists(self) -> bool:
        return self.path.exists()

    def init_new(self, master_password: str, *, kdf_params: Optional[KdfParams] = None) -> None:
        if self.exists():
            raise ValueError(f"Vault already exists at: {self.path}")

        data = VaultData(entries={})
        blob = encrypt_json(data.to_json_dict(), master_password, kdf_params=kdf_params)
        self._write_blob(blob)

    def load(self, master_password: str) -> VaultData:
        blob = self._read_blob()
        obj = decrypt_json(blob, master_password)
        return VaultData.from_json_dict(obj)

    def save(self, master_password: str, data: VaultData) -> None:
        # conserve params KDF existants si possible
        kdf_params = KdfParams()
        if self.exists():
            current = self._read_blob()
            if "kdf" in current:
                kdf_params = KdfParams.from_dict(current["kdf"])

        blob = encrypt_json(data.to_json_dict(), master_password, kdf_params=kdf_params)
        self._write_blob(blob)

    def _read_blob(self) -> Dict:
        if not self.exists():
            raise ValueError(f"No vault found at: {self.path}")
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write_blob(self, blob: Dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(blob, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)
def find_entries(data: VaultData, query: str):
    """
    Recherche simple (case-insensitive) dans title/username/url/notes/tags.
    Si query vide => retourne tout.
    """
    q = (query or "").strip().lower()
    if not q:
        return list(data.entries.values())

    out = []
    for e in data.entries.values():
        hay = " ".join([
            e.title or "",
            e.username or "",
            e.url or "",
            e.notes or "",
            " ".join(e.tags or []),
        ]).lower()
        if q in hay:
            out.append(e)
    return out


def pick_by_id_or_title(data: VaultData, key: str):
    """
    Permet d'identifier une entrée soit:
    - par ID (UUID)
    - par titre exact (case-insensitive)
    """
    if key in data.entries:
        return data.entries[key]

    k = key.strip().lower()
    for e in data.entries.values():
        if (e.title or "").strip().lower() == k:
            return e

    raise ValueError(f"No entry found for '{key}'. Use 'list' to see IDs/titles.")
