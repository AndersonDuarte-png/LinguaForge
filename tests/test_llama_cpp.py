import io
import json

import pytest

from linguaforge.chats import AssistantMessage, Chat, UserMessage
from linguaforge.llama_cpp import (
    LlamaCppTranslationError,
    LlamaCppTranslator,
    LlamaCppTutor,
    LlamaCppTutorError,
    TutorResponseRejected,
    TranslationResponseRejected,
)
from linguaforge.tutor import TutorRequest, TutorResponse
from linguaforge.translation import TranslationRequest


class FakeHttpResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def server_response(**fields):
    return FakeHttpResponse(
        json.dumps({"choices": [{"message": {"content": json.dumps(fields)}}]}).encode()
    )


@pytest.fixture
def tutor_request():
    return TutorRequest(message="Yesterday I go to school.")


@pytest.fixture
def valid_fields():
    return {
        "corrected_text": "Yesterday I went to school.",
        "explanation_pt": "Use 'went' para falar de ontem.",
        "reply_en": "What did you learn at school?",
    }


def test_sends_the_tutor_contract_to_the_local_server(monkeypatch, tutor_request, valid_fields):
    calls = []

    def fake_urlopen(http_request, timeout):
        calls.append((http_request, timeout))
        return server_response(**valid_fields)

    monkeypatch.setattr("linguaforge.llama_cpp.urlopen", fake_urlopen)

    response = LlamaCppTutor(base_url="http://127.0.0.1:18080/").respond(tutor_request)

    http_request, timeout = calls[0]
    payload = json.loads(http_request.data)
    assert response.corrected_text == valid_fields["corrected_text"]
    assert http_request.full_url == "http://127.0.0.1:18080/v1/chat/completions"
    assert timeout == 180
    assert payload["messages"][1]["content"] == tutor_request.message
    assert payload["response_format"]["schema"]["required"] == [
        "corrected_text",
        "explanation_pt",
        "reply_en",
    ]


def test_retries_once_after_a_response_fails_validation(monkeypatch, tutor_request, valid_fields):
    responses = [
        server_response(
            corrected_text="BANANA",
            explanation_pt="A frase está correta.",
            reply_en="What would you like to learn?",
        ),
        server_response(**valid_fields),
    ]
    calls = []

    def fake_urlopen(http_request, timeout):
        calls.append(json.loads(http_request.data))
        return responses.pop(0)

    monkeypatch.setattr("linguaforge.llama_cpp.urlopen", fake_urlopen)

    response = LlamaCppTutor().respond(tutor_request)

    assert response.corrected_text == valid_fields["corrected_text"]
    assert len(calls) == 2
    assert "previous answer was invalid" in calls[1]["messages"][0]["content"]


def test_rejects_the_turn_after_two_invalid_responses(monkeypatch, tutor_request):
    invalid = {
        "corrected_text": "BANANA",
        "explanation_pt": "A frase está correta.",
        "reply_en": "What would you like to learn?",
    }

    monkeypatch.setattr(
        "linguaforge.llama_cpp.urlopen", lambda http_request, timeout: server_response(**invalid)
    )

    with pytest.raises(TutorResponseRejected, match="unrelated"):
        LlamaCppTutor().respond(tutor_request)


def test_rejects_a_malformed_server_response(monkeypatch, tutor_request):
    monkeypatch.setattr(
        "linguaforge.llama_cpp.urlopen",
        lambda http_request, timeout: FakeHttpResponse(b"not json"),
    )

    with pytest.raises(LlamaCppTutorError, match="Could not obtain"):
        LlamaCppTutor().respond(tutor_request)


def test_reports_when_the_local_server_is_available(monkeypatch):
    response = FakeHttpResponse(b'{"status":"ok"}')
    response.status = 200
    monkeypatch.setattr("linguaforge.llama_cpp.urlopen", lambda http_request, timeout: response)

    assert LlamaCppTutor().is_available()


def test_sends_recent_chat_history_with_the_new_tutor_request(monkeypatch, valid_fields):
    chat = Chat()
    history = (
        UserMessage(chat_id=chat.id, text="I goed to work."),
        AssistantMessage(
            chat_id=chat.id,
            response=TutorResponse(
                corrected_text="I went to work.",
                explanation_pt="O passado de 'go' é 'went'.",
                reply_en="How was your day at work?",
            ),
        ),
    )
    calls = []

    def fake_urlopen(http_request, timeout):
        calls.append(json.loads(http_request.data))
        return server_response(**valid_fields)

    monkeypatch.setattr("linguaforge.llama_cpp.urlopen", fake_urlopen)

    LlamaCppTutor().respond(TutorRequest(message="Yesterday I go to school."), history=history)

    assert calls[0]["messages"][1]["content"] == "I goed to work."
    assert json.loads(calls[0]["messages"][2]["content"])["reply_en"] == "How was your day at work?"
    assert calls[0]["messages"][3]["content"] == "Yesterday I go to school."


def test_disables_reply_generation_when_requested(monkeypatch, tutor_request, valid_fields):
    fields_without_reply = {**valid_fields, "reply_en": ""}
    calls = []

    def fake_urlopen(http_request, timeout):
        calls.append(json.loads(http_request.data))
        return server_response(**fields_without_reply)

    monkeypatch.setattr("linguaforge.llama_cpp.urlopen", fake_urlopen)

    response = LlamaCppTutor().respond(tutor_request, include_reply=False)

    assert response.reply_en == ""
    assert "Do not continue the conversation" in calls[0]["messages"][0]["content"]
    assert calls[0]["response_format"]["schema"]["properties"]["reply_en"] == {"type": "string", "const": ""}


def test_translates_a_text_without_sending_chat_history(monkeypatch):
    response_fields = {
        "translation": "Como você está?",
        "interpretation_pt": "Saudação informal.",
    }
    calls = []

    def fake_urlopen(http_request, timeout):
        calls.append(json.loads(http_request.data))
        return server_response(**response_fields)

    monkeypatch.setattr("linguaforge.llama_cpp.urlopen", fake_urlopen)

    response = LlamaCppTranslator().translate(
        TranslationRequest(text="How are you?", source_language="en", target_language="pt")
    )

    assert response.translation == "Como você está?"
    assert len(calls[0]["messages"]) == 2
    assert "Source language: en." in calls[0]["messages"][1]["content"]


def test_rejects_a_malformed_translation_response(monkeypatch):
    monkeypatch.setattr(
        "linguaforge.llama_cpp.urlopen",
        lambda http_request, timeout: server_response(translation="Olá"),
    )

    with pytest.raises(LlamaCppTranslationError, match="Could not obtain"):
        LlamaCppTranslator().translate(
            TranslationRequest(text="Hello", source_language="en", target_language="pt")
        )


@pytest.mark.parametrize("adapter", ["tutor", "translator"])
@pytest.mark.parametrize("body", [
    [],
    {"choices": []},
    {"choices": None},
    {"choices": [None]},
    {"choices": [{"message": {"content": None}}]},
    {"choices": [{"message": {"content": "[]"}}]},
    {"choices": [{"message": {"content": "null"}}]},
])
def test_rejects_malformed_envelopes_without_uncaught_errors(monkeypatch, adapter, body):
    monkeypatch.setattr(
        "linguaforge.llama_cpp.urlopen",
        lambda request, timeout: FakeHttpResponse(json.dumps(body).encode()),
    )
    if adapter == "tutor":
        with pytest.raises(TutorResponseRejected):
            LlamaCppTutor().respond(TutorRequest("Hello!"))
    else:
        with pytest.raises(TranslationResponseRejected):
            LlamaCppTranslator().translate(TranslationRequest("Hello!", "en", "pt"))


def test_retries_malformed_json_once_then_accepts_valid_response(monkeypatch, tutor_request, valid_fields):
    responses = [FakeHttpResponse(b"not json"), server_response(**valid_fields)]
    monkeypatch.setattr("linguaforge.llama_cpp.urlopen", lambda request, timeout: responses.pop(0))

    assert LlamaCppTutor().respond(tutor_request).corrected_text == valid_fields["corrected_text"]
    assert not responses


@pytest.mark.parametrize("adapter", ["tutor", "translator"])
def test_rejects_truncated_output_even_when_json_is_valid(monkeypatch, adapter, valid_fields):
    fields = valid_fields if adapter == "tutor" else {"translation": "Olá", "interpretation_pt": ""}
    body = {"choices": [{"finish_reason": "length", "message": {"content": json.dumps(fields)}}]}
    monkeypatch.setattr(
        "linguaforge.llama_cpp.urlopen", lambda request, timeout: FakeHttpResponse(json.dumps(body).encode())
    )
    if adapter == "tutor":
        with pytest.raises(TutorResponseRejected):
            LlamaCppTutor().respond(TutorRequest("Yesterday I go to school."))
    else:
        with pytest.raises(TranslationResponseRejected):
            LlamaCppTranslator().translate(TranslationRequest("Hello", "en", "pt"))


def test_rejects_empty_translation_but_allows_empty_interpretation(monkeypatch):
    monkeypatch.setattr(
        "linguaforge.llama_cpp.urlopen",
        lambda request, timeout: server_response(translation="  ", interpretation_pt=""),
    )
    with pytest.raises(TranslationResponseRejected):
        LlamaCppTranslator().translate(TranslationRequest("Hello", "en", "pt"))

    monkeypatch.setattr(
        "linguaforge.llama_cpp.urlopen",
        lambda request, timeout: server_response(translation="Olá", interpretation_pt=""),
    )
    assert LlamaCppTranslator().translate(TranslationRequest("Hello", "en", "pt")).translation == "Olá"


@pytest.mark.parametrize("body", [b"not json", b"[]", b'{"status":"loading"}'])
def test_health_check_requires_ready_model_with_short_timeout(monkeypatch, body):
    def fake_urlopen(request, timeout):
        assert timeout == 3
        response = FakeHttpResponse(body)
        response.status = 200
        return response

    monkeypatch.setattr("linguaforge.llama_cpp.urlopen", fake_urlopen)
    assert not LlamaCppTutor().is_available()


def test_does_not_retry_connection_failure(monkeypatch, tutor_request):
    calls = []

    def fail(request, timeout):
        calls.append(request)
        raise ConnectionResetError("connection closed")

    monkeypatch.setattr("linguaforge.llama_cpp.urlopen", fail)
    with pytest.raises(LlamaCppTutorError) as captured:
        LlamaCppTutor().respond(tutor_request)
    assert not isinstance(captured.value, TutorResponseRejected)
    assert len(calls) == 1
    assert not LlamaCppTutor().is_available()


def test_keeps_only_last_twelve_history_messages(monkeypatch, valid_fields, tutor_request):
    chat = Chat()
    history = tuple(UserMessage(chat_id=chat.id, text=f"Message {i}") for i in range(20))
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(json.loads(request.data))
        return server_response(**valid_fields)

    monkeypatch.setattr("linguaforge.llama_cpp.urlopen", fake_urlopen)
    LlamaCppTutor().respond(tutor_request, history=history)
    assert len(calls[0]["messages"]) == 14
    assert calls[0]["messages"][1]["content"] == "Message 8"
    assert calls[0]["messages"][-1]["content"] == tutor_request.message


def test_rejects_reply_when_disabled_even_if_server_ignores_schema(monkeypatch, tutor_request, valid_fields):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(json.loads(request.data))
        return server_response(**valid_fields)

    monkeypatch.setattr("linguaforge.llama_cpp.urlopen", fake_urlopen)
    with pytest.raises(TutorResponseRejected, match="must be empty"):
        LlamaCppTutor().respond(tutor_request, include_reply=False)
    assert len(calls) == 2
