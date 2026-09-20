"""Contrato de domínio para chats independentes e seu armazenamento local."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Protocol, TypeAlias, runtime_checkable
from uuid import UUID, uuid4

from linguaforge.tutor import TutorResponse


HISTORY_MESSAGE_LIMIT = 12


class ChatNotFoundError(ValueError):
    """O chat deixou de existir antes de concluir a operação."""


class ChatChangedError(ValueError):
    """Outra mensagem foi salva enquanto o tutor preparava a resposta."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Chat:
    """Uma conversa selecionada na barra lateral de chats."""

    id: UUID = field(default_factory=uuid4)
    title: str = "New Chat"
    created_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True)
class UserMessage:
    """Uma mensagem escrita pelo aluno em um chat."""

    chat_id: UUID
    text: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_utc_now)
    role: Literal["user"] = field(default="user", init=False)


@dataclass(frozen=True)
class AssistantMessage:
    """Uma resposta estruturada do tutor exibida como mensagem do assistente."""

    chat_id: UUID
    response: TutorResponse
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_utc_now)
    role: Literal["assistant"] = field(default="assistant", init=False)


ChatMessage: TypeAlias = UserMessage | AssistantMessage


@runtime_checkable
class ChatStore(Protocol):
    """Operações de persistência local exigidas pela interface de chat."""

    def create_chat(self, chat: Chat) -> None:
        """Persiste um chat recém-criado."""

    def list_chats(self) -> tuple[Chat, ...]:
        """Retorna os chats na ordem usada pela barra lateral."""

    def get_chat(self, chat_id: UUID) -> Chat | None:
        """Busca um chat pelo identificador."""

    def rename_chat(self, chat_id: UUID, title: str) -> None:
        """Atualiza o título de um chat existente."""

    def list_messages(self, chat_id: UUID, *, limit: int | None = None) -> tuple[ChatMessage, ...]:
        """Retorna o histórico cronológico, opcionalmente só as mensagens recentes."""

    def add_message(self, message: ChatMessage) -> None:
        """Persiste uma mensagem em seu chat."""

    def add_turn(
        self,
        user_message: UserMessage,
        assistant_message: AssistantMessage,
        *,
        expected_last_message_id: UUID | None,
    ) -> None:
        """Persiste o turno inteiro se o histórico usado pelo tutor continua atual."""

    def delete_chat(self, chat_id: UUID) -> None:
        """Exclui um chat e todas as suas mensagens."""
