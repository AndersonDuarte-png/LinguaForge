"""Contrato de domínio para tradução e interpretação sem histórico."""

from dataclasses import dataclass
from typing import Literal


Language = Literal["en", "pt"]


@dataclass(frozen=True)
class TranslationRequest:
    """Texto isolado e direção escolhida para a tradução."""

    text: str
    source_language: Language
    target_language: Language

    def __post_init__(self) -> None:
        if self.source_language not in ("en", "pt") or self.target_language not in ("en", "pt"):
            raise ValueError("Supported languages are English and Portuguese.")
        if self.source_language == self.target_language:
            raise ValueError("Source and target languages must be different.")


@dataclass(frozen=True)
class TranslationResponse:
    """Tradução direta e interpretação breve para falantes de português."""

    translation: str
    interpretation_pt: str
