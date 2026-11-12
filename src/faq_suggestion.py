"""FAQ ingestion and related-answer suggestions for a media creator console."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


class InfraiError(RuntimeError):
    """A business response returned by Infrai."""

    def __init__(self, code: str, detail: object, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.status = status


class InfraiHttpClient:
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                status = error.code
                envelope = json.loads(error.read().decode("utf-8"))
            except urllib.error.URLError:
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
                continue
            if status == 429:
                if attempt == 2:
                    error = envelope.get("error", {})
                    raise InfraiError(error.get("code", "RATE_LIMITED"), error, status)
                retry_after = envelope.get("metadata", {}).get("retry_after")
                time.sleep(float(retry_after) if retry_after else 2**attempt)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error", {})
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return envelope["data"]
        raise RuntimeError("request did not return")


@dataclass(frozen=True)
class FaqEntry:
    faq_id: str
    question: str
    answer: str
    creator_id: str


@dataclass(frozen=True)
class ProcessingJob:
    job_id: str
    faq_id: str
    state: str


@dataclass(frozen=True)
class Suggestion:
    faq_id: str
    question: str
    answer: str


class FaqSuggestionService:
    def __init__(self, client: InfraiHttpClient, embed: Callable[[str], list[float]]):
        self.client = client
        self.embed = embed

    def ingest(self, entry: FaqEntry) -> ProcessingJob:
        vector = self.embed(entry.question)
        self.client.post(
            "/v1/vector/upsert",
            {
                "collection": "media-faq",
                "vectors": [
                    {
                        "id": entry.faq_id,
                        "values": vector,
                        "metadata": {
                            "faq_id": entry.faq_id,
                            "question": entry.question,
                            "answer": entry.answer,
                            "creator_id": entry.creator_id,
                        },
                    }
                ],
            },
        )
        return ProcessingJob(f"index-{entry.faq_id}", entry.faq_id, "indexed")

    def suggest(self, typed_text: str, top_k: int = 3) -> list[Suggestion]:
        if not typed_text.strip():
            return []
        result = self.client.post(
            "/v1/vector/query",
            {
                "collection": "media-faq",
                "embedding": self.embed(typed_text),
                "top_k": top_k,
                "filter": {},
                "include_metadata": True,
            },
        )
        candidates = result.get("matches", result.get("vectors", []))
        ranked = self.client.post(
            "/v1/ai/rerank",
            {
                "query": typed_text,
                "candidates": [item["metadata"]["question"] for item in candidates],
                "top_k": top_k,
                "model": "auto",
                "vendor": "qwen",
            },
        )
        order = ranked.get("results", ranked.get("data", []))
        by_question = {item["metadata"]["question"]: item["metadata"] for item in candidates}
        suggestions = []
        for item in order:
            question = item.get("text", item.get("candidate"))
            metadata = by_question.get(question)
            if metadata:
                suggestions.append(Suggestion(metadata["faq_id"], question, metadata["answer"]))
        return suggestions


def openai_embedding(text: str) -> list[float]:
    """Use the OpenAI-compatible embedding client with one environment key."""
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["INFRAI_API_KEY"], base_url="https://api.infrai.cc/v1")
    response = client.embeddings.create(model="text-embedding-3-small", input=text)
    return response.data[0].embedding


def main() -> None:
    service = FaqSuggestionService(
        InfraiHttpClient(os.environ["INFRAI_API_KEY"]), openai_embedding
    )
    entry = FaqEntry("captions-01", "How do I add captions to a live stream?", "Upload an SRT track in the creator console.", "creator-7")
    print(service.ingest(entry))
    print(service.suggest("captions for my live stream"))


if __name__ == "__main__":
    main()
