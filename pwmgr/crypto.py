from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag


def b64e(b: bytes) -> str:
    return base64.b64encode(b).decode("utf-8")


def b64d(s: str) -> bytes:
    return base64.b64decode(s.encode("utf-8"))


@dataclass(frozen=True)
class KdfParams:
    """
    Paramètres Argon2id :
    - time_cost/memory_cost ralentissent le brute-force.
    """
    time_cost: int = 3
    memory_cost_kib: int = 64 * 1024  # 64 MiB
    parallelism: int = 2
    hash_len: int = 32               # 32 bytes => 256-bit key
    salt_len: int = 16

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "argon2id",
            "time_cost": self.time_cost,
            "memory_cost_kib": self.memory_cost_kib,
            "parallelism": self.parallelism,
            "hash_len": self.hash_len,
            "salt_len": self.salt_len,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "KdfParams":
        return KdfParams(
            time_cost=int(d.get("time_cost", 3)),
            memory_cost_kib=int(d.get("memory_cost_kib", 64 * 1024)),
            parallelism=int(d.get("parallelism", 2)),
            hash_len=int(d.get("hash_len", 32)),
            salt_len=int(d.get("salt_len", 16)),
        )


def derive_key(master_password: str, salt: bytes, params: KdfParams) -> bytes:
    if not master_password:
        raise ValueError("Master password must be non-empty.")

    return hash_secret_raw(
        secret=master_password.encode("utf-8"),
        salt=salt,
        time_cost=params.time_cost,
        memory_cost=params.memory_cost_kib,
        parallelism=params.parallelism,
        hash_len=params.hash_len,
        type=Type.ID,  # Argon2id
    )


def encrypt_json(
    obj: Dict[str, Any],
    master_password: str,
    *,
    kdf_params: Optional[KdfParams] = None,
    salt: Optional[bytes] = None,
) -> Dict[str, Any]:
    """
    Retourne un "blob" JSON contenant uniquement du chiffré + paramètres.
    """
    kdf_params = kdf_params or KdfParams()
    salt = salt or os.urandom(kdf_params.salt_len)

    key = derive_key(master_password, salt, kdf_params)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)

    plaintext = json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")

    # AAD: on authentifie aussi le header (version/kdf/salt)
    header = {"version": 1, "kdf": kdf_params.to_dict(), "salt": b64e(salt)}
    aad = json.dumps(header, sort_keys=True).encode("utf-8")

    ciphertext = aesgcm.encrypt(nonce, plaintext, aad)

    return {
        **header,
        "nonce": b64e(nonce),
        "ciphertext": b64e(ciphertext),
    }


def decrypt_json(blob: Dict[str, Any], master_password: str) -> Dict[str, Any]:
    try:
        version = int(blob["version"])
        if version != 1:
            raise ValueError(f"Unsupported crypto version: {version}")

        kdf_params = KdfParams.from_dict(blob["kdf"])
        salt = b64d(blob["salt"])
        nonce = b64d(blob["nonce"])
        ciphertext = b64d(blob["ciphertext"])

        header = {"version": 1, "kdf": kdf_params.to_dict(), "salt": b64e(salt)}
        aad = json.dumps(header, sort_keys=True).encode("utf-8")

        key = derive_key(master_password, salt, kdf_params)
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, aad)

        return json.loads(plaintext.decode("utf-8"))

    except InvalidTag:
        raise ValueError("Wrong master password OR vault file tampered.") from None
    except KeyError as e:
        raise ValueError(f"Vault missing field: {e}") from None