from pathlib import Path
import sqlite3

import pytest

from linguaforge.chats import Chat, UserMessage
from linguaforge.sqlite_store import SqliteChatStore
from linguaforge.storage_import import import_chat_history


def test_import_preserves_history_source_and_independent_backup(tmp_path):
    source = tmp_path / "source.sqlite3"
    destination = tmp_path / "installed/chats.sqlite3"
    store = SqliteChatStore(source)
    chat = Chat(title="My original chat")
    message = UserMessage(chat_id=chat.id, text="Hello")
    store.create_chat(chat)
    store.add_message(message)
    original = source.read_bytes()
    backup = import_chat_history(source, destination)
    assert source.read_bytes() == original
    assert SqliteChatStore(destination).list_messages(chat.id) == (message,)
    SqliteChatStore(destination).delete_chat(chat.id)
    assert SqliteChatStore(backup).list_chats() == (chat,)
    assert SqliteChatStore(source).list_chats() == (chat,)


def test_import_never_overwrites_an_existing_database(tmp_path):
    source, destination = tmp_path / "source.sqlite3", tmp_path / "destination.sqlite3"
    SqliteChatStore(source)
    destination.write_bytes(b"existing data")
    with pytest.raises(FileExistsError):
        import_chat_history(source, destination)
    assert destination.read_bytes() == b"existing data"


@pytest.mark.parametrize("kind", ["missing", "garbage", "unrelated"])
def test_invalid_source_leaves_no_destination(tmp_path, kind):
    source, destination = tmp_path / "source.sqlite3", tmp_path / "installed/chats.sqlite3"
    if kind == "garbage":
        source.write_bytes(b"not sqlite")
    elif kind == "unrelated":
        with sqlite3.connect(source) as connection:
            connection.execute("CREATE TABLE unrelated (id INTEGER)")
    with pytest.raises((ValueError, FileNotFoundError, sqlite3.DatabaseError)):
        import_chat_history(source, destination)
    assert not destination.exists()


def test_import_includes_committed_wal_data(tmp_path):
    source, destination = tmp_path / "source.sqlite3", tmp_path / "installed/chats.sqlite3"
    store = SqliteChatStore(source)
    with sqlite3.connect(source) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        chat = Chat(title="From WAL")
        connection.execute("INSERT INTO chats (id, title, created_at) VALUES (?, ?, ?)",
                           (str(chat.id), chat.title, chat.created_at.isoformat()))
        connection.commit()
        assert Path(str(source) + "-wal").exists()
        import_chat_history(source, destination)
        assert SqliteChatStore(destination).list_chats() == (chat,)
