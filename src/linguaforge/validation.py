"""Validação determinística das respostas do tutor textual."""

from dataclasses import dataclass
from difflib import SequenceMatcher

from linguaforge.tutor import TutorRequest, TutorResponse

_MIN_CORRECTION_SIMILARITY = 0.5


@dataclass(frozen=True)
class TutorResponseValidation:
    """Resultado da verificação de uma resposta do tutor contra sua solicitação."""

    accepted: bool
    issues: tuple[str, ...] = ()


def validate_tutor_response(
    request: TutorRequest, response: TutorResponse, *, require_reply: bool = True
) -> TutorResponseValidation:
    """Rejeita respostas malformadas e correções sem relação com a mensagem do aluno."""
    issues = tuple(
        f"{field} must not be empty."
        for field, value in (
            (
                ("corrected_text", response.corrected_text),
                ("explanation_pt", response.explanation_pt),
            )
            + ((("reply_en", response.reply_en),) if require_reply else ())
        )
        if not value.strip()
    )

    if not require_reply and response.reply_en != "":
        issues += ("reply_en must be empty when disabled.",)

    similarity = SequenceMatcher(
        None, request.message.casefold(), response.corrected_text.casefold(), autojunk=False
    ).ratio()
    if response.corrected_text.strip() and similarity < _MIN_CORRECTION_SIMILARITY:
        issues += ("corrected_text is unrelated to the student message.",)

    return TutorResponseValidation(accepted=not issues, issues=issues)
