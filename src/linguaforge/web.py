"""API local que fornece os dados da interface web."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Literal
from uuid import UUID

import uvicorn
from fastapi import FastAPI, HTTPException, Response, status
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from linguaforge.chats import (
    HISTORY_MESSAGE_LIMIT,
    AssistantMessage,
    Chat,
    ChatChangedError,
    ChatMessage,
    ChatNotFoundError,
    UserMessage,
)
from linguaforge.config import Config, get_config
from linguaforge.llama_cpp import (
    LlamaCppTranslationError,
    LlamaCppTranslator,
    LlamaCppTutor,
    LlamaCppTutorError,
    TranslationResponseRejected,
    TutorResponseRejected,
)
from linguaforge.sqlite_store import SqliteChatStore
from linguaforge.tutor import TutorRequest
from linguaforge.translation import TranslationRequest


class UserMessageInput(BaseModel):
    """Corpo da requisição para uma nova mensagem do aluno."""

    text: str
    include_reply: bool = True


class ChatTitleInput(BaseModel):
    """Corpo da requisição para renomear um chat."""

    title: str


class TranslationInput(BaseModel):
    """Corpo da requisição para uma tradução isolada."""

    text: str
    source_language: Literal["en", "pt"]
    target_language: Literal["en", "pt"]


def create_app(
    database_path: Path | None = None,
    tutor: LlamaCppTutor | None = None,
    translator: LlamaCppTranslator | None = None,
    *,
    config: Config | None = None,
) -> FastAPI:
    """Cria a API local com um armazenamento de chats isolado."""
    app_config = config or get_config()
    store = SqliteChatStore(database_path or app_config.data_dir / "chats.sqlite3")
    local_tutor = tutor or LlamaCppTutor()
    local_translator = translator or LlamaCppTranslator()
    app = FastAPI(title="LinguaForge")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/tutor/availability")
    def tutor_availability() -> dict[str, bool]:
        return {"available": local_tutor.is_available()}

    @app.post("/api/translate")
    def translate(payload: TranslationInput) -> dict[str, str]:
        if not payload.text.strip():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Text is empty.")
        try:
            request = TranslationRequest(
                text=payload.text,
                source_language=payload.source_language,
                target_language=payload.target_language,
            )
            response = local_translator.translate(request)
        except ValueError as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
        except TranslationResponseRejected as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The translator returned an invalid response. Please try again.",
            ) from error
        except LlamaCppTranslationError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Translator is unavailable. Start llama-server and try again.",
            ) from error
        return asdict(response)

    @app.get("/api/chats")
    def list_chats() -> list[dict[str, str]]:
        return [_serialize_chat(chat) for chat in store.list_chats()]

    @app.post("/api/chats", status_code=status.HTTP_201_CREATED)
    def create_chat() -> dict[str, str]:
        chat = Chat()
        store.create_chat(chat)
        return _serialize_chat(chat)

    @app.patch("/api/chats/{chat_id}")
    def rename_chat(chat_id: UUID, payload: ChatTitleInput) -> dict[str, str]:
        chat = _require_chat(store, chat_id)
        title = payload.title.strip()
        if not title:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Title is empty.")
        if len(title) > 80:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Title must contain at most 80 characters.",
            )
        try:
            store.rename_chat(chat_id, title)
        except ChatNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found."
            ) from error
        return _serialize_chat(Chat(id=chat.id, title=title, created_at=chat.created_at))

    @app.get("/api/chats/{chat_id}/messages")
    def list_messages(chat_id: UUID) -> list[dict[str, object]]:
        _require_chat(store, chat_id)
        return [_serialize_message(message) for message in store.list_messages(chat_id)]

    @app.post("/api/chats/{chat_id}/messages", status_code=status.HTTP_201_CREATED)
    def add_user_message(chat_id: UUID, payload: UserMessageInput) -> dict[str, object]:
        _require_chat(store, chat_id)
        if not payload.text.strip():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Message is empty.")
        history = store.list_messages(chat_id, limit=HISTORY_MESSAGE_LIMIT)
        try:
            tutor_response = local_tutor.respond(
                TutorRequest(message=payload.text),
                history=history,
                include_reply=payload.include_reply,
            )
        except TutorResponseRejected as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The tutor returned an invalid response. Please try again.",
            ) from error
        except LlamaCppTutorError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Tutor is unavailable. Start llama-server and try again.",
            ) from error
        message = UserMessage(chat_id=chat_id, text=payload.text)
        assistant_message = AssistantMessage(chat_id=chat_id, response=tutor_response)
        try:
            store.add_turn(
                message,
                assistant_message,
                expected_last_message_id=history[-1].id if history else None,
            )
        except ChatNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found."
            ) from error
        except ChatChangedError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This chat received another message. Reload it and try again.",
            ) from error
        return {
            "user_message": _serialize_message(message),
            "assistant_message": _serialize_message(assistant_message),
        }

    @app.delete("/api/chats/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_chat(chat_id: UUID) -> Response:
        _require_chat(store, chat_id)
        store.delete_chat(chat_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    frontend_dist = app_config.frontend_dir
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

    return app


def run() -> None:
    """Inicia a API local para desenvolvimento."""
    uvicorn.run(create_app(), host="127.0.0.1", port=8000)


def _require_chat(store: SqliteChatStore, chat_id: UUID) -> Chat:
    chat = store.get_chat(chat_id)
    if chat is not None:
        return chat
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")


def _serialize_chat(chat: Chat) -> dict[str, str]:
    return {
        "id": str(chat.id),
        "title": chat.title,
        "created_at": chat.created_at.isoformat(),
    }


def _serialize_message(message: ChatMessage) -> dict[str, object]:
    serialized: dict[str, object] = {
        "id": str(message.id),
        "chat_id": str(message.chat_id),
        "role": message.role,
        "created_at": message.created_at.isoformat(),
    }
    if isinstance(message, UserMessage):
        return {**serialized, "text": message.text}
    if isinstance(message, AssistantMessage):
        return {**serialized, "response": asdict(message.response)}
    raise TypeError("Unsupported chat message.")
