"""Deterministic validation for text tutor responses."""

from dataclasses import dataclass
from difflib import SequenceMatcher

from linguaforge.tutor import TutorRequest, TutorResponse

_MIN_CORRECTION_SIMILARITY = 0.5


@dataclass(frozen=True)
class TutorResponseValidation:
    """The result of checking a tutor response against its request."""

    accepted: bool
    issues: tuple[str, ...] = ()


def validate_tutor_response(
    request: TutorRequest, response: TutorResponse
) -> TutorResponseValidation:
    """Reject malformed responses and corrections unrelated to the student message."""
    issues = tuple(
        f"{field} must not be empty."
        for field, value in (
            ("corrected_text", response.corrected_text),
            ("explanation_pt", response.explanation_pt),
            ("reply_en", response.reply_en),
        )
        if not value.strip()
    )

    similarity = SequenceMatcher(
        None, request.message.casefold(), response.corrected_text.casefold()
    ).ratio()
    if response.corrected_text.strip() and similarity < _MIN_CORRECTION_SIMILARITY:
        issues += ("corrected_text is unrelated to the student message.",)

    return TutorResponseValidation(accepted=not issues, issues=issues)
