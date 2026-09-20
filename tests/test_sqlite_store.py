from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import sqlite3
from threading import Barrier

import pytest
from uuid import uuid4

from linguaforge.chats import AssistantMessage, Chat, ChatChangedError, ChatNotFoundError, UserMessage
from linguaforge.sqlite_store import SqliteChatStore
from linguaforge.tutor import TutorResponse


def test_persists_chats_between_store_instances(tmp_path):
    database_path = tmp_path / "linguaforge.sqlite3"
    older_chat = Chat(id=uuid4(), title="First chat", created_at=datetime(2026, 9, 18, tzinfo=timezone.utc))
    newer_chat = Chat(id=uuid4(), title="New Chat", created_at=datetime(2026, 9, 19, tzinfo=timezone.utc))

    store = SqliteChatStore(database_path)
    store.create_chat(older_chat)
    store.create_chat(newer_chat)

    persisted_chats = SqliteChatStore(database_path).list_chats()

    assert persisted_chats == (newer_chat, older_chat)


def test_persists_messages_in_chronological_order(tmp_path):
    store = SqliteChatStore(tmp_path / "linguaforge.sqlite3")
    chat = Chat()
    store.create_chat(chat)
    user_message = UserMessage(
        chat_id=chat.id,
        text="I goed to work.",
        created_at=datetime(2026, 9, 19, 10, tzinfo=timezone.utc),
    )
    assistant_message = AssistantMessage(
        chat_id=chat.id,
        response=TutorResponse(
            corrected_text="I went to work.",
            explanation_pt="O passado de 'go' é 'went'.",
            reply_en="How was your day at work?",
        ),
        created_at=datetime(2026, 9, 19, 10, 1, tzinfo=timezone.utc),
    )
    store.add_message(user_message)
    store.add_message(assistant_message)

    messages = store.list_messages(chat.id)

    assert messages == (user_message, assistant_message)


def test_deleting_a_chat_also_deletes_its_messages(tmp_path):
    store = SqliteChatStore(tmp_path / "linguaforge.sqlite3")
    chat = Chat()
    store.create_chat(chat)
    store.add_message(UserMessage(chat_id=chat.id, text="Hello!"))

    store.delete_chat(chat.id)

    assert store.list_chats() == ()
    assert store.list_messages(chat.id) == ()


def test_renames_a_chat_and_persists_the_new_title(tmp_path):
    database_path = tmp_path / "linguaforge.sqlite3"
    store = SqliteChatStore(database_path)
    chat = Chat(title="New Chat")
    store.create_chat(chat)

    store.rename_chat(chat.id, "Travel plans")

    assert SqliteChatStore(database_path).list_chats()[0].title == "Travel plans"


def _turn(chat_id):
    return (
        UserMessage(chat_id=chat_id, text="I went to work."),
        AssistantMessage(
            chat_id=chat_id,
            response=TutorResponse(
                corrected_text="I went to work.",
                explanation_pt="A frase já está correta.",
                reply_en="How was work?",
            ),
        ),
    )


def test_finds_one_chat_without_changing_its_data(tmp_path):
    store = SqliteChatStore(tmp_path / "chats.sqlite3")
    chat = Chat()
    store.create_chat(chat)

    assert store.get_chat(chat.id) == chat
    assert store.get_chat(uuid4()) is None


def test_reads_only_the_latest_messages_in_order_and_keeps_chats_isolated(tmp_path):
    store = SqliteChatStore(tmp_path / "chats.sqlite3")
    chat, other_chat = Chat(), Chat()
    store.create_chat(chat)
    store.create_chat(other_chat)
    timestamp = datetime(2026, 9, 19, tzinfo=timezone.utc)
    messages = tuple(
        UserMessage(chat_id=chat.id, text=f"Message {index}", created_at=timestamp)
        for index in range(15)
    )
    for message in messages:
        store.add_message(message)
    store.add_message(UserMessage(chat_id=other_chat.id, text="Private to another chat"))

    assert store.list_messages(chat.id, limit=12) == messages[-12:]
    assert store.list_messages(chat.id) == messages
    assert store.list_messages(uuid4(), limit=12) == ()
    with pytest.raises(ValueError, match="positivo"):
        store.list_messages(chat.id, limit=0)


def test_turn_survives_reopening_the_store(tmp_path):
    path = tmp_path / "chats.sqlite3"
    store = SqliteChatStore(path)
    chat = Chat()
    store.create_chat(chat)
    turn = _turn(chat.id)

    store.add_turn(*turn, expected_last_message_id=None)

    assert SqliteChatStore(path).list_messages(chat.id) == turn


def test_rolls_back_the_user_message_if_saving_the_assistant_fails(tmp_path):
    store = SqliteChatStore(tmp_path / "chats.sqlite3")
    chat = Chat()
    store.create_chat(chat)
    user, assistant = _turn(chat.id)
    # A restrição UNIQUE falha na segunda gravação, após a mensagem do aluno.
    assistant = AssistantMessage(chat_id=chat.id, response=assistant.response, id=user.id)

    with pytest.raises(sqlite3.IntegrityError):
        store.add_turn(user, assistant, expected_last_message_id=None)

    assert store.list_messages(chat.id) == ()


def test_rejects_turns_whose_messages_belong_to_different_chats(tmp_path):
    store = SqliteChatStore(tmp_path / "chats.sqlite3")
    first, second = Chat(), Chat()
    store.create_chat(first)
    store.create_chat(second)
    user, _ = _turn(first.id)
    _, assistant = _turn(second.id)

    with pytest.raises(ValueError, match="mesmo chat"):
        store.add_turn(user, assistant, expected_last_message_id=None)

    assert store.list_messages(first.id) == ()
    assert store.list_messages(second.id) == ()


def test_rejects_turn_and_rename_after_chat_deletion(tmp_path):
    store = SqliteChatStore(tmp_path / "chats.sqlite3")
    chat = Chat()
    store.create_chat(chat)
    store.delete_chat(chat.id)

    with pytest.raises(ChatNotFoundError):
        store.add_turn(*_turn(chat.id), expected_last_message_id=None)
    with pytest.raises(ChatNotFoundError):
        store.rename_chat(chat.id, "A title that must not resurrect the chat")
    assert store.list_chats() == ()
    assert store.list_messages(chat.id) == ()


def test_concurrent_turns_cannot_overwrite_each_others_context(tmp_path):
    store = SqliteChatStore(tmp_path / "chats.sqlite3")
    chat = Chat()
    store.create_chat(chat)
    barrier = Barrier(2)

    def save_turn(_):
        turn = _turn(chat.id)
        barrier.wait(timeout=5)
        try:
            store.add_turn(*turn, expected_last_message_id=None)
            return turn
        except ChatChangedError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(save_turn, range(2)))

    accepted = [turn for turn in results if turn is not None]
    assert len(accepted) == 1
    assert store.list_messages(chat.id) == accepted[0]


def test_concurrent_turns_for_different_chats_are_both_saved(tmp_path):
    store = SqliteChatStore(tmp_path / "chats.sqlite3")
    chats = (Chat(), Chat())
    for chat in chats:
        store.create_chat(chat)
    barrier = Barrier(2)

    def save_turn(chat):
        turn = _turn(chat.id)
        barrier.wait(timeout=5)
        store.add_turn(*turn, expected_last_message_id=None)
        return turn

    with ThreadPoolExecutor(max_workers=2) as pool:
        turns = list(pool.map(save_turn, chats))

    for chat, turn in zip(chats, turns, strict=True):
        assert store.list_messages(chat.id) == turn
