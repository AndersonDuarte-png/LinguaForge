from fastapi.testclient import TestClient
import pytest
from uuid import uuid4

from linguaforge.chats import AssistantMessage, Chat, UserMessage
from linguaforge.llama_cpp import (
    LlamaCppTranslationError,
    LlamaCppTutorError,
    TranslationResponseRejected,
    TutorResponseRejected,
)
from linguaforge.sqlite_store import SqliteChatStore
from linguaforge.tutor import TutorResponse
from linguaforge.translation import TranslationResponse
from linguaforge.web import create_app


class FakeTutor:
    def __init__(self):
        self.history = ()

    def respond(self, request, *, history=(), include_reply=True):
        self.history = history
        return TutorResponse(
            corrected_text="I went to work.",
            explanation_pt="O passado de 'go' é 'went'.",
            reply_en="How was your day at work?" if include_reply else "",
        )

    def is_available(self):
        return True


class FakeTranslator:
    def translate(self, request):
        return TranslationResponse(
            translation="Como você está?",
            interpretation_pt="Saudação informal.",
        )


def test_creates_lists_and_deletes_independent_chats(tmp_path):
    client = TestClient(create_app(tmp_path / "chats.sqlite3"))

    created = client.post("/api/chats")
    chat = created.json()

    assert created.status_code == 201
    assert chat["title"] == "New Chat"
    assert client.get("/api/chats").json() == [chat]
    assert client.get(f"/api/chats/{chat['id']}/messages").json() == []
    assert client.delete(f"/api/chats/{chat['id']}").status_code == 204
    assert client.get("/api/chats").json() == []


def test_returns_not_found_for_a_missing_chat(tmp_path):
    client = TestClient(create_app(tmp_path / "chats.sqlite3"))

    response = client.get("/api/chats/2b405630-0d72-4e5b-ba8c-a0e3e7bf2528/messages")

    assert response.status_code == 404


def test_renames_a_chat_and_returns_the_updated_title(tmp_path):
    client = TestClient(create_app(tmp_path / "chats.sqlite3"))
    chat_id = client.post("/api/chats").json()["id"]

    response = client.patch(f"/api/chats/{chat_id}", json={"title": "Travel plans"})

    assert response.status_code == 200
    assert response.json()["title"] == "Travel plans"
    assert client.get("/api/chats").json()[0]["title"] == "Travel plans"
    assert client.patch(f"/api/chats/{chat_id}", json={"title": "  "}).status_code == 422


def test_returns_user_and_structured_assistant_messages(tmp_path):
    database_path = tmp_path / "chats.sqlite3"
    store = SqliteChatStore(database_path)
    chat = Chat(id=uuid4())
    store.create_chat(chat)
    store.add_message(UserMessage(chat_id=chat.id, text="I goed to work."))
    store.add_message(
        AssistantMessage(
            chat_id=chat.id,
            response=TutorResponse(
                corrected_text="I went to work.",
                explanation_pt="O passado de 'go' é 'went'.",
                reply_en="How was your day at work?",
            ),
        )
    )

    messages = TestClient(create_app(database_path)).get(f"/api/chats/{chat.id}/messages").json()

    assert messages[0]["role"] == "user"
    assert messages[0]["text"] == "I goed to work."
    assert messages[1]["role"] == "assistant"
    assert messages[1]["response"]["reply_en"] == "How was your day at work?"


def test_adds_a_user_message_to_the_selected_chat(tmp_path):
    client = TestClient(create_app(tmp_path / "chats.sqlite3", tutor=FakeTutor()))
    chat_id = client.post("/api/chats").json()["id"]

    created = client.post(f"/api/chats/{chat_id}/messages", json={"text": "Hello!"})

    assert created.status_code == 201
    assert created.json()["user_message"]["role"] == "user"
    assert created.json()["user_message"]["text"] == "Hello!"
    assert created.json()["assistant_message"]["role"] == "assistant"
    assert client.post(f"/api/chats/{chat_id}/messages", json={"text": "  "}).status_code == 422


def test_can_disable_the_tutor_reply_for_one_message(tmp_path):
    client = TestClient(create_app(tmp_path / "chats.sqlite3", tutor=FakeTutor()))
    chat_id = client.post("/api/chats").json()["id"]

    response = client.post(
        f"/api/chats/{chat_id}/messages",
        json={"text": "I goed to work.", "include_reply": False},
    )

    assert response.status_code == 201
    assert response.json()["assistant_message"]["response"]["reply_en"] == ""


def test_keeps_the_chat_unchanged_when_the_tutor_is_unavailable(tmp_path):
    class UnavailableTutor:
        def respond(self, request, *, history=(), include_reply=True):
            raise LlamaCppTutorError("The server is unavailable.")

        def is_available(self):
            return False

    client = TestClient(create_app(tmp_path / "chats.sqlite3", tutor=UnavailableTutor()))
    chat_id = client.post("/api/chats").json()["id"]

    response = client.post(f"/api/chats/{chat_id}/messages", json={"text": "Hello!"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Tutor is unavailable. Start llama-server and try again."
    assert client.get(f"/api/chats/{chat_id}/messages").json() == []
    assert client.get("/api/tutor/availability").json() == {"available": False}


def test_translates_without_creating_a_chat_or_message(tmp_path):
    client = TestClient(
        create_app(tmp_path / "chats.sqlite3", tutor=FakeTutor(), translator=FakeTranslator())
    )

    response = client.post(
        "/api/translate",
        json={"text": "How are you?", "source_language": "en", "target_language": "pt"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "translation": "Como você está?",
        "interpretation_pt": "Saudação informal.",
    }
    assert client.get("/api/chats").json() == []


def test_sends_only_recent_history_from_the_selected_chat_to_the_tutor(tmp_path):
    path = tmp_path / "chats.sqlite3"
    tutor = FakeTutor()
    client = TestClient(create_app(path, tutor=tutor))
    store = SqliteChatStore(path)
    chat, other = Chat(), Chat()
    store.create_chat(chat)
    store.create_chat(other)
    history = []
    for index in range(16):
        message = UserMessage(chat_id=chat.id, text=f"Message {index}")
        store.add_message(message)
        history.append(message)
    store.add_message(UserMessage(chat_id=other.id, text="Another chat's private message"))

    response = client.post(f"/api/chats/{chat.id}/messages", json={"text": "Hello!"})

    assert response.status_code == 201
    assert tutor.history == tuple(history[-12:])
    assert len(store.list_messages(chat.id)) == 18
    assert len(store.list_messages(other.id)) == 1


def test_returns_not_found_if_chat_is_deleted_during_generation(tmp_path):
    path = tmp_path / "chats.sqlite3"
    store = SqliteChatStore(path)
    chat = Chat()
    store.create_chat(chat)

    class DeletingTutor(FakeTutor):
        def respond(self, request, **kwargs):
            store.delete_chat(chat.id)
            return super().respond(request, **kwargs)

    client = TestClient(create_app(path, tutor=DeletingTutor()))
    response = client.post(f"/api/chats/{chat.id}/messages", json={"text": "Hello!"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Chat not found."
    assert store.list_messages(chat.id) == ()


def test_returns_conflict_when_another_turn_changes_the_used_context(tmp_path):
    path = tmp_path / "chats.sqlite3"
    store = SqliteChatStore(path)
    chat = Chat()
    store.create_chat(chat)
    competing_user = UserMessage(chat_id=chat.id, text="Another tab sent this.")
    competing_reply = AssistantMessage(
        chat_id=chat.id,
        response=TutorResponse("Another tab sent this.", "A frase está correta.", "What next?"),
    )

    class CompetingTutor(FakeTutor):
        def respond(self, request, **kwargs):
            store.add_turn(competing_user, competing_reply, expected_last_message_id=None)
            return super().respond(request, **kwargs)

    client = TestClient(create_app(path, tutor=CompetingTutor()))
    response = client.post(f"/api/chats/{chat.id}/messages", json={"text": "Hello!"})

    assert response.status_code == 409
    assert store.list_messages(chat.id) == (competing_user, competing_reply)


def test_returns_not_found_if_chat_is_deleted_during_rename(tmp_path, monkeypatch):
    path = tmp_path / "chats.sqlite3"
    client = TestClient(create_app(path))
    chat_id = client.post("/api/chats").json()["id"]
    original_rename = SqliteChatStore.rename_chat

    def deleting_rename(store, identifier, title):
        store.delete_chat(identifier)
        original_rename(store, identifier, title)

    monkeypatch.setattr(SqliteChatStore, "rename_chat", deleting_rename)
    response = client.patch(f"/api/chats/{chat_id}", json={"title": "Updated title"})

    assert response.status_code == 404
    assert client.get("/api/chats").json() == []


def test_title_boundaries_trim_and_persist_without_changing_other_chats(tmp_path):
    path = tmp_path / "chats.sqlite3"
    client = TestClient(create_app(path))
    first = client.post("/api/chats").json()
    second = client.post("/api/chats").json()
    route = f"/api/chats/{first['id']}"

    assert client.patch(route, json={"title": "  Travel plans  "}).json()["title"] == "Travel plans"
    assert client.patch(route, json={"title": "x" * 80}).status_code == 200
    assert client.patch(route, json={"title": "x" * 81}).status_code == 422
    assert client.patch(route, json={"title": "   "}).status_code == 422
    assert client.patch(route, json={"title": None}).status_code == 422
    persisted = {chat["id"]: chat for chat in TestClient(create_app(path)).get("/api/chats").json()}
    assert persisted[first["id"]]["title"] == "x" * 80
    assert persisted[second["id"]] == second


def test_rejected_tutor_response_is_not_reported_as_an_offline_server(tmp_path):
    class RejectingTutor(FakeTutor):
        def respond(self, request, **kwargs):
            raise TutorResponseRejected("Invalid model output")

    client = TestClient(create_app(tmp_path / "chats.sqlite3", tutor=RejectingTutor()))
    chat_id = client.post("/api/chats").json()["id"]

    response = client.post(f"/api/chats/{chat_id}/messages", json={"text": "Hello!"})

    assert response.status_code == 502
    assert "invalid response" in response.json()["detail"]
    assert client.get(f"/api/chats/{chat_id}/messages").json() == []
    assert client.get("/api/tutor/availability").json() == {"available": True}


@pytest.mark.parametrize(
    ("error_type", "status_code"),
    [(TranslationResponseRejected, 502), (LlamaCppTranslationError, 503)],
)
def test_translation_distinguishes_invalid_output_from_an_offline_server(tmp_path, error_type, status_code):
    class FailingTranslator:
        def translate(self, request):
            raise error_type("Translation failed")

    client = TestClient(create_app(tmp_path / "chats.sqlite3", translator=FailingTranslator()))
    response = client.post(
        "/api/translate",
        json={"text": "Hello!", "source_language": "en", "target_language": "pt"},
    )

    assert response.status_code == status_code
    assert client.get("/api/chats").json() == []


@pytest.mark.parametrize(
    "payload",
    [
        {"text": " ", "source_language": "en", "target_language": "pt"},
        {"text": "Hello!", "source_language": "en", "target_language": "en"},
        {"text": "Hello!", "source_language": "fr", "target_language": "pt"},
        {"text": None, "source_language": "en", "target_language": "pt"},
    ],
)
def test_invalid_translation_input_does_not_call_the_model(tmp_path, payload):
    class UnexpectedTranslator:
        def translate(self, request):
            pytest.fail("Invalid input must not reach the model")

    client = TestClient(create_app(tmp_path / "chats.sqlite3", translator=UnexpectedTranslator()))

    assert client.post("/api/translate", json=payload).status_code == 422


def test_installed_app_serves_packaged_resources_and_keeps_database_outside_bundle(tmp_path, monkeypatch):
    from dataclasses import replace
    from linguaforge.config import get_config

    resources = tmp_path / "readonly-bundle/frontend"
    resources.mkdir(parents=True)
    (resources / "index.html").write_text("<html>Packaged LinguaForge</html>")
    cfg = replace(get_config(), frontend_dir=resources, data_dir=tmp_path / "user-data")
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(config=cfg))
    assert "Packaged LinguaForge" in client.get("/").text
    chat = client.post("/api/chats").json()
    assert client.get("/api/chats").json() == [chat]
    assert (cfg.data_dir / "chats.sqlite3").exists()
    assert not tuple(resources.glob("*.sqlite3"))
