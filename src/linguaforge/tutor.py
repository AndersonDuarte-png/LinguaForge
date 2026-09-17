"""Domain contract for one text-based tutoring turn."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TutorRequest:
    """The student's original message written in English."""

    message: str


@dataclass(frozen=True)
class TutorResponse:
    """Correction, explanation, and conversation reply for a tutoring turn."""

    corrected_text: str  # Corrected student message in English.
    explanation_pt: str  # Short explanation in Portuguese.
    reply_en: str  # Tutor's reply in English to continue the conversation.
