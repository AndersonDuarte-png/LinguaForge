import io
import json

import pytest

from linguaforge.llama_cpp import LlamaCppTutor, LlamaCppTutorError, TutorResponseRejected
from linguaforge.tutor import TutorRequest


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
