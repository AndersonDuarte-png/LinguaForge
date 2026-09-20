"""Persistência local dos chats em SQLite."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from uuid import UUID

from linguaforge.chats import (
    AssistantMessage,
    Chat,
    ChatChangedError,
    ChatMessage,
    ChatNotFoundError,
    UserMessage,
)
from linguaforge.tutor import TutorResponse


class SqliteChatStore:
    """Implementação SQLite do contrato de armazenamento dos chats."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def create_chat(self, chat: Chat) -> None:
        """Salva um chat vazio."""
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "INSERT INTO chats (id, title, created_at) VALUES (?, ?, ?)",
                (str(chat.id), chat.title, chat.created_at.isoformat()),
            )

    def list_chats(self) -> tuple[Chat, ...]:
        """Retorna os chats mais recentes primeiro para a barra lateral."""
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                "SELECT id, title, created_at FROM chats ORDER BY created_at DESC, id DESC"
            ).fetchall()
        return tuple(
            Chat(id=UUID(row[0]), title=row[1], created_at=self._read_datetime(row[2]))
            for row in rows
        )

    def get_chat(self, chat_id: UUID) -> Chat | None:
        """Busca diretamente um chat, sem carregar toda a barra lateral."""
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT id, title, created_at FROM chats WHERE id = ?",
                (str(chat_id),),
            ).fetchone()
        if row is None:
            return None
        return Chat(id=UUID(row[0]), title=row[1], created_at=self._read_datetime(row[2]))

    def rename_chat(self, chat_id: UUID, title: str) -> None:
        """Atualiza o título ou sinaliza que o chat foi excluído."""
        with closing(self._connect()) as connection, connection:
            updated = connection.execute(
                "UPDATE chats SET title = ? WHERE id = ?",
                (title, str(chat_id)),
            )
            if updated.rowcount == 0:
                raise ChatNotFoundError("O chat não existe.")

    def list_messages(self, chat_id: UUID, *, limit: int | None = None) -> tuple[ChatMessage, ...]:
        """Retorna o histórico cronológico; limita a leitura quando usado como contexto."""
        if limit is not None and limit < 1:
            raise ValueError("O limite deve ser positivo.")
        query = """
            SELECT id, role, text, corrected_text, explanation_pt, reply_en, created_at
            FROM messages
            WHERE chat_id = ?
        """
        parameters: tuple[object, ...] = (str(chat_id),)
        if limit is None:
            query += " ORDER BY created_at, sequence"
        else:
            query += " ORDER BY created_at DESC, sequence DESC LIMIT ?"
            parameters += (limit,)
        with closing(self._connect()) as connection:
            rows = connection.execute(query, parameters).fetchall()
        if limit is not None:
            rows.reverse()
        return tuple(self._message_from_row(chat_id, row) for row in rows)

    def add_message(self, message: ChatMessage) -> None:
        """Salva uma mensagem do aluno ou a resposta estruturada do tutor."""
        with closing(self._connect()) as connection, connection:
            self._insert_message(connection, message)

    def add_turn(
        self,
        user_message: UserMessage,
        assistant_message: AssistantMessage,
        *,
        expected_last_message_id: UUID | None,
    ) -> None:
        """Salva o par de mensagens em uma única transação, sem perder concorrência."""
        if user_message.chat_id != assistant_message.chat_id:
            raise ValueError("As mensagens do turno devem pertencer ao mesmo chat.")
        with closing(self._connect()) as connection, connection:
            # Reserva a escrita antes de conferir o histórico para evitar uma corrida.
            connection.execute("BEGIN IMMEDIATE")
            exists = connection.execute(
                "SELECT 1 FROM chats WHERE id = ?", (str(user_message.chat_id),)
            ).fetchone()
            if exists is None:
                raise ChatNotFoundError("O chat não existe.")
            last = connection.execute(
                """
                SELECT id FROM messages WHERE chat_id = ?
                ORDER BY created_at DESC, sequence DESC LIMIT 1
                """,
                (str(user_message.chat_id),),
            ).fetchone()
            last_message_id = UUID(last[0]) if last else None
            if last_message_id != expected_last_message_id:
                raise ChatChangedError("O histórico mudou durante a geração da resposta.")
            self._insert_message(connection, user_message)
            self._insert_message(connection, assistant_message)

    @staticmethod
    def _insert_message(connection: sqlite3.Connection, message: ChatMessage) -> None:
        if isinstance(message, UserMessage):
            fields = (message.text, None, None, None)
        elif isinstance(message, AssistantMessage):
            fields = (
                None,
                message.response.corrected_text,
                message.response.explanation_pt,
                message.response.reply_en,
            )
        else:
            raise TypeError("Tipo de mensagem não suportado.")
        try:
            connection.execute(
                """
                INSERT INTO messages (
                    id, chat_id, role, text, corrected_text, explanation_pt, reply_en, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(message.id),
                    str(message.chat_id),
                    message.role,
                    *fields,
                    message.created_at.isoformat(),
                ),
            )
        except sqlite3.IntegrityError as error:
            if error.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_FOREIGNKEY:
                raise ChatNotFoundError("O chat da mensagem não existe.") from error
            raise

    def delete_chat(self, chat_id: UUID) -> None:
        """Remove um chat e suas mensagens."""
        with closing(self._connect()) as connection, connection:
            connection.execute("DELETE FROM chats WHERE id = ?", (str(chat_id),))

    def _initialize(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS chats (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    id TEXT NOT NULL UNIQUE,
                    chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    text TEXT,
                    corrected_text TEXT,
                    explanation_pt TEXT,
                    reply_en TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _read_datetime(value: str) -> datetime:
        return datetime.fromisoformat(value)

    @staticmethod
    def _message_from_row(chat_id: UUID, row: tuple[object, ...]) -> ChatMessage:
        message_id, role, text, corrected_text, explanation_pt, reply_en, created_at = row
        if role == "user":
            return UserMessage(
                id=UUID(str(message_id)),
                chat_id=chat_id,
                text=str(text),
                created_at=SqliteChatStore._read_datetime(str(created_at)),
            )
        return AssistantMessage(
            id=UUID(str(message_id)),
            chat_id=chat_id,
            response=TutorResponse(
                corrected_text=str(corrected_text),
                explanation_pt=str(explanation_pt),
                reply_en=str(reply_en),
            ),
            created_at=SqliteChatStore._read_datetime(str(created_at)),
        )
