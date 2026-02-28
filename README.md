# pwmgr — Password Manager (local vault)

Un gestionnaire de mots de passe minimal:
- Vault local **chiffré**
- CLI: init/add/list/show/copy/update/delete
- Copie au presse-papiers avec auto-clear
- Audit (faible / réutilisé)
- Backup export/import + change-master

## Installation
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
