from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid


def now_utc_iso() -> str:
    """Timestamp UTC ISO8601."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Entry:
    """
    Une entrée de compte.
    Le mot de passe est en clair en mémoire (le vault sur disque est chiffré).
    """
    id: str
    title: str
    username: str
    password: str
    url: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    @staticmethod
    def new(
        title: str,
        username: str,
        password: str,
        url: Optional[str] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> "Entry":
        ts = now_utc_iso()
        return Entry(
            id=str(uuid.uuid4()),
            title=title,
            username=username,
            password=password,
            url=url,
            notes=notes,
            tags=tags or [],
            created_at=ts,
            updated_at=ts,
        )

    def touch(self) -> None:
        self.updated_at = now_utc_iso()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Entry":
        # compat: si tags absent/None dans un vieux vault
        tags = d.get("tags") or []
        return Entry(
            id=d["id"],
            title=d["title"],
            username=d["username"],
            password=d["password"],
            url=d.get("url"),
            notes=d.get("notes"),
            tags=list(tags),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
        )


@dataclass
class VaultData:
    """Contenu logique du coffre (avant chiffrement)."""
    entries: Dict[str, Entry]
    version: int = 1

    def to_json_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "entries": {eid: e.to_dict() for eid, e in self.entries.items()},
        }

    @staticmethod
    def from_json_dict(d: Dict[str, Any]) -> "VaultData":
        raw = d.get("entries", {})
        entries = {eid: Entry.from_dict(ed) for eid, ed in raw.items()}
        return VaultData(entries=entries, version=int(d.get("version", 1)))