from dataclasses import FrozenInstanceError

import pytest

from linguaforge.tutor import TutorRequest, TutorResponse


def test_tutor_contract_represents_a_text_turn():
    request = TutorRequest(message="Yesterday I go to school.")
    response = TutorResponse(
        corrected_text="Yesterday I went to school.",
        explanation_pt="Use 'went', passado de 'go', para falar de ontem.",
        reply_en="What did you learn at school?",
    )

    assert request.message == "Yesterday I go to school."
    assert response.corrected_text == "Yesterday I went to school."
    assert response.explanation_pt == "Use 'went', passado de 'go', para falar de ontem."
    assert response.reply_en == "What did you learn at school?"


@pytest.mark.parametrize(
    ("value", "field"),
    [
        (TutorRequest(message="I like reading."), "message"),
        (
            TutorResponse(
                corrected_text="I like reading.",
                explanation_pt="A frase está correta.",
                reply_en="What do you like to read?",
            ),
            "reply_en",
        ),
    ],
)
def test_tutor_contract_is_immutable(value, field):
    with pytest.raises(FrozenInstanceError):
        setattr(value, field, "Changed text")
