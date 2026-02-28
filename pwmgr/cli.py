from getpass import getpass
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .models import Entry
from .utils import generate_password, copy_to_clipboard_autoclear, normalize_tags
from .audit import audit_vault
from .backup import export_vault_data, import_vault_data
from .vault import Vault, DEFAULT_VAULT_PATH, find_entries, pick_by_id_or_title

console = Console()
app = typer.Typer(add_completion=False, help="pwmgr - password manager (MVP)")

@app.callback()
def root():
    """Gestionnaire de mots de passe (vault chiffré local)."""
    pass


def ask_master(confirm: bool = False, prompt: str = "Master password: ") -> str:
    """
    Demande un mot de passe de manière cachée (getpass).
    - confirm=True : demande 2 fois (utile pour init/change-master/import)
    """
    pw = getpass(prompt)
    if confirm:
        pw2 = getpass("Confirm: ")
        if pw != pw2:
            raise typer.BadParameter("Passwords do not match.")
    if not pw:
        raise typer.BadParameter("Password cannot be empty.")
    return pw


def resolve_vault_path(path: Optional[Path]) -> Path:
    return path or DEFAULT_VAULT_PATH


@app.command()
def version():
    """Affiche la version."""
    console.print(f"pwmgr version: [bold]{__version__}[/]")


@app.command()
def init(path: Optional[Path] = typer.Option(None, "--path", help="Chemin du vault")):
    """Crée un nouveau vault chiffré (vide)."""
    vault = Vault(resolve_vault_path(path))
    master = ask_master(confirm=True)
    vault.init_new(master)
    console.print(f"[green]Vault created:[/] {vault.path}")


@app.command()
def info(path: Optional[Path] = typer.Option(None, "--path", help="Chemin du vault")):
    """Vérifie mot de passe + affiche nombre d’entrées."""
    vault = Vault(resolve_vault_path(path))
    master = ask_master()
    data = vault.load(master)
    console.print(f"[green]Vault OK[/]  Path: {vault.path}")
    console.print(f"Entries: [bold]{len(data.entries)}[/]")


@app.command()
def add(
    title: str = typer.Option(..., prompt=True),
    username: str = typer.Option(..., prompt=True),
    password: Optional[str] = typer.Option(None, help="Mot de passe (sinon prompt)"),
    gen: bool = typer.Option(False, "--gen", help="Générer un mot de passe fort"),
    length: int = typer.Option(20, "--length", help="Longueur si --gen"),
    url: Optional[str] = typer.Option(None),
    notes: Optional[str] = typer.Option(None),
    tags: Optional[str] = typer.Option(None, help="Tags séparés par virgule"),
    path: Optional[Path] = typer.Option(None, "--path"),
):
    """Ajoute une entrée."""
    vault = Vault(resolve_vault_path(path))
    master = ask_master()
    data = vault.load(master)

    if gen:
        password = generate_password(length=length, with_symbols=True)
        console.print("[yellow]Password generated.[/] (non affiché)")
    if not password:
        password = getpass("Account password: ")
        if not password:
            raise typer.BadParameter("Account password cannot be empty.")

    e = Entry.new(
        title=title,
        username=username,
        password=password,
        url=url,
        notes=notes,
        tags=normalize_tags(tags),
    )
    data.entries[e.id] = e
    vault.save(master, data)

    console.print(f"[green]Added:[/] {e.title}  [dim]{e.id}[/]")


@app.command()
def list(
    q: Optional[str] = typer.Option(None, "--q", help="Recherche"),
    path: Optional[Path] = typer.Option(None, "--path"),
):
    """Liste les entrées (avec recherche optionnelle)."""
    vault = Vault(resolve_vault_path(path))
    master = ask_master()
    data = vault.load(master)

    entries = find_entries(data, q or "")

    table = Table(title="Entries")
    table.add_column("ID", style="dim")
    table.add_column("Title")
    table.add_column("Username")
    table.add_column("URL")
    table.add_column("Tags")

    for e in sorted(entries, key=lambda x: (x.title or "").lower()):
        table.add_row(e.id, e.title, e.username, e.url or "", ", ".join(e.tags or []))

    console.print(table)


@app.command()
def show(
    key: str = typer.Argument(..., help="ID ou titre exact"),
    reveal: bool = typer.Option(False, "--reveal", help="Afficher le mot de passe (déconseillé)"),
    path: Optional[Path] = typer.Option(None, "--path"),
):
    """Affiche une entrée (mot de passe caché par défaut)."""
    vault = Vault(resolve_vault_path(path))
    master = ask_master()
    data = vault.load(master)

    e = pick_by_id_or_title(data, key)

    console.print(f"[bold]{e.title}[/]")
    console.print(f"Username: {e.username}")
    console.print(f"URL: {e.url or ''}")
    console.print(f"Tags: {', '.join(e.tags or [])}")
    console.print(f"Created: {e.created_at}")
    console.print(f"Updated: {e.updated_at}")
    if e.notes:
        console.print(f"Notes: {e.notes}")

    console.print("Password: [dim]******** (use copy)[/]" if not reveal else f"[red]Password:[/] {e.password}")


@app.command()
def copy(
    key: str = typer.Argument(..., help="ID ou titre exact"),
    seconds: int = typer.Option(20, "--seconds", help="Auto-clear presse-papiers"),
    path: Optional[Path] = typer.Option(None, "--path"),
):
    """Copie le mot de passe dans le presse-papiers puis efface après N secondes."""
    vault = Vault(resolve_vault_path(path))
    master = ask_master()
    data = vault.load(master)

    e = pick_by_id_or_title(data, key)
    copy_to_clipboard_autoclear(e.password, seconds=seconds)
    console.print(f"[green]Copied[/] {e.title} [dim](auto-clear {seconds}s)[/]")


@app.command()
def update(
    key: str = typer.Argument(..., help="ID ou titre exact"),
    title: Optional[str] = typer.Option(None),
    username: Optional[str] = typer.Option(None),
    url: Optional[str] = typer.Option(None),
    notes: Optional[str] = typer.Option(None),
    tags: Optional[str] = typer.Option(None, help="Tags (virgules)"),
    ask_password: bool = typer.Option(False, "--ask-password", help="Demander le mot de passe via prompt caché"),
    gen: bool = typer.Option(False, "--gen", help="Générer un nouveau mot de passe"),
    length: int = typer.Option(20, "--length"),
    path: Optional[Path] = typer.Option(None, "--path"),
):
    """Met à jour une entrée (sans toucher aux champs non fournis)."""
    vault = Vault(resolve_vault_path(path))
    master = ask_master()
    data = vault.load(master)

    e = pick_by_id_or_title(data, key)

    if title is not None: e.title = title
    if username is not None: e.username = username
    if url is not None: e.url = url
    if notes is not None: e.notes = notes
    if tags is not None: e.tags = normalize_tags(tags)

    if gen:
        e.password = generate_password(length=length, with_symbols=True)
        console.print("[yellow]Password generated.[/] (non affiché)")
    elif ask_password:
        new_pw = getpass("New account password: ")
        if not new_pw:
            raise typer.BadParameter("Account password cannot be empty.")
        e.password = new_pw

    e.touch()
    vault.save(master, data)
    console.print(f"[green]Updated:[/] {e.title}")


@app.command()
def audit(
    min_length: int = typer.Option(12, "--min-length"),
    path: Optional[Path] = typer.Option(None, "--path"),
):
    """Audit: mots de passe faibles + réutilisés (sans afficher les secrets)."""
    vault = Vault(resolve_vault_path(path))
    master = ask_master()
    data = vault.load(master)

    weak, reused = audit_vault(data, min_length=min_length)

    console.print(f"[bold]Audit[/] for {vault.path}")
    console.print(f"Weak passwords: [bold]{len(weak)}[/]")
    console.print(f"Reused passwords groups: [bold]{len(reused)}[/]")

    if weak:
        t = Table(title="Weak passwords (no secrets shown)")
        t.add_column("Title")
        t.add_column("Username")
        t.add_column("Reasons")
        for f in sorted(weak, key=lambda x: x.entry.title.lower()):
            t.add_row(f.entry.title, f.entry.username, ", ".join(f.reasons))
        console.print(t)

    if reused:
        t2 = Table(title="Reused passwords (groups)")
        t2.add_column("Group", style="dim")
        t2.add_column("Accounts (title -> username)")
        for i, (_fp, entries) in enumerate(reused.items(), start=1):
            accounts = " | ".join([f"{e.title} -> {e.username}" for e in entries])
            t2.add_row(f"G{i}", accounts)
        console.print(t2)


@app.command("change-master")
def change_master(
    path: Optional[Path] = typer.Option(None, "--path"),
):
    """
    Change le mot de passe maître du vault (re-chiffrement complet).
    """
    vault = Vault(resolve_vault_path(path))
    old = ask_master(prompt="Current master password: ")
    data = vault.load(old)

    new = ask_master(confirm=True, prompt="New master password: ")
    vault.save(new, data)

    console.print("[green]Master password changed.[/]")


@app.command()
def export(
    out: Path = typer.Option(..., "--out", help="Chemin du fichier de backup (ex: .\\backup.vault.json)"),
    path: Optional[Path] = typer.Option(None, "--path", help="Chemin du vault source"),
    reencrypt: bool = typer.Option(False, "--reencrypt", help="Demander un mot de passe de backup différent"),
):
    """
    Exporte un backup.
    - Par défaut: déchiffre puis rechiffre avec le même master (backup identique mais nouveau salt/nonce).
    - Si --reencrypt: tu choisis un mot de passe de backup différent.
    """
    vault = Vault(resolve_vault_path(path))
    master = ask_master(prompt="Source master password: ")
    data = vault.load(master)

    out_pw = master
    if reencrypt:
        out_pw = ask_master(confirm=True, prompt="Backup password: ")

    export_vault_data(data, out, out_pw)
    console.print(f"[green]Exported backup:[/] {out}")


@app.command()
def import_(
    inp: Path = typer.Option(..., "--in", help="Chemin du fichier backup à importer"),
    path: Optional[Path] = typer.Option(None, "--path", help="Chemin du vault cible"),
    use_source_password: bool = typer.Option(False, "--use-source-password", help="Réutiliser le mot de passe du backup"),
):
    """
    Importe un backup en REMPLAÇANT le vault cible (simple & sûr).
    - On déchiffre le backup avec son mot de passe
    - On rechiffre dans le vault cible avec:
        - soit un nouveau master
        - soit le même que le backup (--use-source-password)
    """
    target = Vault(resolve_vault_path(path))

    src_pw = ask_master(prompt="Backup password: ")
    data = import_vault_data(inp, src_pw)

    if use_source_password:
        new_pw = src_pw
    else:
        new_pw = ask_master(confirm=True, prompt="New master password for target vault: ")

    # Ecrit/re-chiffre dans la cible
    target.save(new_pw, data)
    console.print(f"[green]Imported[/] into {target.path}")


@app.command()
def delete(
    key: str = typer.Argument(..., help="ID ou titre exact"),
    yes: bool = typer.Option(False, "--yes"),
    path: Optional[Path] = typer.Option(None, "--path"),
):
    """Supprime une entrée."""
    vault = Vault(resolve_vault_path(path))
    master = ask_master()
    data = vault.load(master)

    e = pick_by_id_or_title(data, key)

    if not yes:
        if not typer.confirm(f"Delete '{e.title}'?"):
            raise typer.Abort()

    del data.entries[e.id]
    vault.save(master, data)
    console.print(f"[green]Deleted:[/] {e.title}")


def main():
    app()