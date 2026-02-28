from pathlib import Path
from pwmgr.vault import Vault
from pwmgr.models import Entry

def test_vault_file_roundtrip(tmp_path: Path):
    path = tmp_path / "vault.json"
    v = Vault(path)
    v.init_new("master")
    data = v.load("master")

    e = Entry.new("Gmail", "me", "secret", url="https://gmail.com", tags=["mail"])
    data.entries[e.id] = e
    v.save("master", data)

    data2 = v.load("master")
    assert len(data2.entries) == 1
    e2 = list(data2.entries.values())[0]
    assert e2.title == "Gmail"
    assert e2.password == "secret"