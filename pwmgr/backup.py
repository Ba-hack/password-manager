from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from .crypto import decrypt_json, encrypt_json, KdfParams
from .models import VaultData


def read_blob(path: Path) -> Dict:
    """Lit un fichier vault chiffré (JSON)."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_blob_atomic(path: Path, blob: Dict) -> None:
    """
    Ecriture atomique: .tmp puis replace
    => évite les fichiers corrompus.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(blob, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def export_vault_data(data: VaultData, out_path: Path, out_password: str, kdf_params: KdfParams | None = None) -> None:
    """Rechiffre VaultData vers un fichier de backup chiffré."""
    blob = encrypt_json(data.to_json_dict(), out_password, kdf_params=kdf_params)
    write_blob_atomic(out_path, blob)


def import_vault_data(in_path: Path, in_password: str) -> VaultData:
    """Déchiffre un fichier vault/backup et renvoie VaultData."""
    blob = read_blob(in_path)
    obj = decrypt_json(blob, in_password)
    return VaultData.from_json_dict(obj)