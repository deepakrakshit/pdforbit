from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import httpx

from app.core.config import AppSettings


class TranslationServiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class TranslationRequest:
    text: str
    target_language: str
    source_language: str | None = None


@dataclass(frozen=True)
class SummaryRequest:
    text: str
    output_language: str = "en"
    length: Literal["short", "medium", "long"] = "medium"
    focus: str | None = None


def chunk_text(text: str, *, max_chars: int) -> list[str]:
    normalized = text.strip()
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [normalized]

    chunks: list[str] = []
    current: list[str] = []
    current_size = 0

    for paragraph in [item.strip() for item in normalized.split("\n") if item.strip()]:
        paragraph_parts = [paragraph]
        if len(paragraph) > max_chars:
            paragraph_parts = _split_large_text(paragraph, max_chars=max_chars)

        for part in paragraph_parts:
            part_size = len(part) + (2 if current else 0)
            if current and current_size + part_size > max_chars:
                chunks.append("\n\n".join(current))
                current = [part]
                current_size = len(part)
                continue
            current.append(part)
            current_size += part_size

    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _split_large_text(text: str, *, max_chars: int) -> list[str]:
    sentences = [item.strip() for item in text.replace("\r", "").split(". ") if item.strip()]
    if len(sentences) <= 1:
        return [text[index:index + max_chars].strip() for index in range(0, len(text), max_chars) if text[index:index + max_chars].strip()]

    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = sentence if not current else f"{current}. {sentence}"
        if len(candidate) > max_chars and current:
            chunks.append(current)
            current = sentence
            continue
        current = candidate
    if current:
        chunks.append(current)
    return chunks


class TranslationService:
    def __init__(self, settings: AppSettings, *, http_client: httpx.Client | None = None) -> None:
        self._settings = settings
        self._http_client = http_client

    def _provider(self) -> str:
        return self._settings.translation_provider.strip().lower()

    def _not_configured_message(self, capability: Literal["translation", "summarization"]) -> str:
        action = "translation jobs" if capability == "translation" else "AI summary jobs"
        return (
            f"AI {capability} is not configured. Set TRANSLATION_PROVIDER=groq and add GROQ_API_KEY "
            f"to enable {action}."
        )

    def _unsupported_provider_message(self, capability: Literal["translation", "summarization"]) -> str:
        return f"Unsupported AI provider '{self._settings.translation_provider}' for {capability}."

    def translate(self, request: TranslationRequest) -> str:
        provider = self._provider()
        if provider in {"", "disabled", "none"}:
            raise TranslationServiceError(self._not_configured_message("translation"))
        if provider == "mock":
            source = request.source_language or "auto"
            return f"[{source}->{request.target_language}] {request.text}"
        if provider == "groq":
            source = request.source_language or "auto-detect"
            return self._chat_completion(
                model=self._settings.groq_translate_model,
                temperature=0.15,
                max_completion_tokens=4096,
                system_prompt=(
                    "You are a professional document translator. Translate the provided document text faithfully "
                    "into the requested target language. Preserve headings, bullets, paragraph breaks, numbering, "
                    "and legal or technical meaning. Do not add commentary or explanations."
                ),
                user_prompt=(
                    f"Source language: {source}\n"
                    f"Target language: {request.target_language}\n\n"
                    "Translate the following document text exactly and return only the translated text:\n\n"
                    f"{request.text}"
                ),
            )

        raise TranslationServiceError(self._unsupported_provider_message("translation"))

    def summarize(self, request: SummaryRequest) -> str:
        provider = self._provider()
        if provider in {"", "disabled", "none"}:
            raise TranslationServiceError(self._not_configured_message("summarization"))
        if provider == "mock":
            focus = f" focus={request.focus};" if request.focus else ""
            return f"[summary:{request.length}:{request.output_language}{focus}] {request.text[:200]}"
        if provider == "groq":
            focus_line = f"Priority focus: {request.focus}\n" if request.focus else ""
            length_instruction = {
                "short": "Keep the brief tight: 4-6 bullets plus a one-paragraph overview.",
                "medium": "Provide a concise executive brief with overview, key points, and action items.",
                "long": "Provide a detailed brief with overview, major findings, risks, and recommended next steps.",
            }[request.length]
            return self._chat_completion(
                model=self._settings.groq_summary_model,
                temperature=0.2,
                max_completion_tokens={"short": 700, "medium": 1200, "long": 1800}[request.length],
                system_prompt=(
                    "You are an enterprise document analyst. Produce accurate, useful PDF summaries for busy "
                    "professionals. Favor clear structure, factual compression, and zero fluff."
                ),
                user_prompt=(
                    f"Output language: {request.output_language}\n"
                    f"Summary length: {request.length}\n"
                    f"{focus_line}"
                    f"{length_instruction}\n\n"
                    "Summarize the following extracted PDF text. Return plain text with a title, short overview, "
                    "and clearly separated bullet sections when useful. Do not mention that the text was extracted "
                    "or speculate beyond the source.\n\n"
                    f"{request.text}"
                ),
            )

        raise TranslationServiceError(self._unsupported_provider_message("summarization"))

    def _chat_completion(
        self,
        *,
        model: str,
        temperature: float,
        max_completion_tokens: int,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        api_key = self._settings.translation_api_key or self._settings.groq_api_key
        if not api_key:
            raise TranslationServiceError(
                "Groq API key is not configured. Add GROQ_API_KEY to the backend service to enable AI jobs."
            )

        payload = {
            "model": model,
            "temperature": temperature,
            "max_completion_tokens": max_completion_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        client = self._http_client
        should_close = False
        if client is None:
            client = httpx.Client(
                base_url=self._settings.groq_api_base.rstrip("/"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self._settings.groq_timeout_seconds,
            )
            should_close = True

        try:
            response = client.post("/chat/completions", json=payload)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise TranslationServiceError("Groq request timed out while processing the document.") from exc
        except httpx.HTTPStatusError as exc:
            message = _extract_http_error(exc.response)
            raise TranslationServiceError(f"Groq request failed: {message}") from exc
        except httpx.HTTPError as exc:
            raise TranslationServiceError("Groq request failed because the AI provider is unreachable.") from exc
        finally:
            if should_close:
                client.close()

        body = response.json()
        choices = body.get("choices") or []
        if not choices:
            raise TranslationServiceError("Groq returned an empty response.")
        message = choices[0].get("message") or {}
        content = (message.get("content") or "").strip()
        if not content:
            raise TranslationServiceError("Groq returned an empty completion.")
        return content


def _extract_http_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip() or response.reason_phrase

    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if message:
            return str(message)
    if isinstance(error, str) and error.strip():
        return error.strip()
    return response.text.strip() or response.reason_phrase
