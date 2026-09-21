"""Importação explícita do banco local, preservando a origem e um backup."""

from contextlib import closing
from pathlib import Path
import os
import sqlite3
from shutil import copyfileobj
from tempfile import NamedTemporaryFile
from uuid import uuid4


def import_chat_history(source: Path, destination: Path) -> Path:
    """Copia um snapshot consistente; nunca substitui um banco de destino existente."""
    source = source.resolve()
    destination = destination.absolute()
    if destination.exists():
        raise FileExistsError(f"Chat database already exists: {destination}")
    if not source.is_file():
        raise FileNotFoundError(source)
    temporary_path = None
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original:
        if original.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise ValueError("The source database is not healthy.")
        tables = {row[0] for row in original.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"chats", "messages"}.issubset(tables):
            raise ValueError("The source is not a LinguaForge chat database.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        backup_dir = destination.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        backup = backup_dir / f"chats-before-import-{uuid4().hex}.sqlite3"
        try:
            with NamedTemporaryFile(dir=destination.parent, prefix=".chat-import-", delete=False) as temporary:
                temporary_path = Path(temporary.name)
            with closing(sqlite3.connect(temporary_path)) as snapshot:
                original.backup(snapshot)
            # O backup e o destino são arquivos distintos; editar o destino não muda o backup.
            with temporary_path.open("rb") as snapshot_file, backup.open("xb") as output:
                copyfileobj(snapshot_file, output)
            os.chmod(backup, 0o600)
            # Um link atômico publica o snapshot sem sobrescrever destino criado em paralelo.
            os.link(temporary_path, destination)
            return backup
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
