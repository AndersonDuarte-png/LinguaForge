import pytest

from linguaforge.translation import TranslationRequest, TranslationResponse


def test_represents_a_translation_without_chat_history():
    request = TranslationRequest(text="How are you?", source_language="en", target_language="pt")
    response = TranslationResponse(translation="Como você está?", interpretation_pt="Saudação informal.")

    assert request.text == "How are you?"
    assert response.translation == "Como você está?"


def test_rejects_equal_source_and_target_languages():
    with pytest.raises(ValueError, match="different"):
        TranslationRequest(text="Hello", source_language="en", target_language="en")


@pytest.mark.parametrize("source,target", [("es", "en"), ("en", "fr")])
def test_rejects_unsupported_languages(source, target):
    with pytest.raises(ValueError, match="Supported languages"):
        TranslationRequest(text="Hello", source_language=source, target_language=target)
