"""Contrato de domínio para um turno do tutor textual."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TutorRequest:
    """Mensagem original do aluno, escrita em inglês."""

    message: str


@dataclass(frozen=True)
class TutorResponse:
    """Correção, explicação e resposta de continuidade de um turno do tutor."""

    corrected_text: str  # Mensagem do aluno corrigida em inglês.
    explanation_pt: str  # Explicação breve em português.
    reply_en: str  # Continuação em inglês; vazia quando Reply estiver desabilitado.
