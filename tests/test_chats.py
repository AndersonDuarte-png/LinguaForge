from datetime import datetime, timezone
from uuid import uuid4

from linguaforge.chats import AssistantMessage, Chat, ChatStore, UserMessage
from linguaforge.tutor import TutorResponse


def test_new_chat_has_a_default_title_and_utc_timestamp():
    chat = Chat()

    assert chat.title == "New Chat"
    assert chat.id
    assert chat.created_at.tzinfo == timezone.utc


def test_user_message_belongs_to_one_chat():
    chat_id = uuid4()
    created_at = datetime(2026, 9, 19, tzinfo=timezone.utc)

    message = UserMessage(chat_id=chat_id, text="I goed to work.", created_at=created_at)

    assert message.chat_id == chat_id
    assert message.text == "I goed to work."
    assert message.role == "user"
    assert message.created_at == created_at


def test_assistant_message_preserves_the_structured_tutor_response():
    response = TutorResponse(
        corrected_text="I went to work.",
        explanation_pt="O passado de 'go' é 'went'.",
        reply_en="How was your day at work?",
    )

    message = AssistantMessage(chat_id=uuid4(), response=response)

    assert message.response == response
    assert message.role == "assistant"


def test_store_contract_covers_the_required_chat_operations():
    class InMemoryStore:
        def create_chat(self, chat: Chat) -> None:
            pass

        def list_chats(self) -> tuple[Chat, ...]:
            return ()

        def get_chat(self, chat_id):
            return None

        def rename_chat(self, chat_id, title: str) -> None:
            pass

        def list_messages(self, chat_id, *, limit=None):
            return ()

        def add_message(self, message) -> None:
            pass

        def add_turn(self, user_message, assistant_message, *, expected_last_message_id):
            pass

        def delete_chat(self, chat_id) -> None:
            pass

    assert isinstance(InMemoryStore(), ChatStore)
