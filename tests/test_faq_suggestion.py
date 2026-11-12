from faq_suggestion import FaqEntry, FaqSuggestionService, InfraiHttpClient


def test_typed_media_question_returns_ranked_creator_answer():
    calls = []
    responses = [
        {},
        {"matches": [{"metadata": {"faq_id": "a", "question": "How do I add captions?", "answer": "Upload an SRT track."}}]},
        {"results": [{"text": "How do I add captions?"}]},
    ]

    def fake_post(path, payload):
        calls.append((path, payload))
        return responses.pop(0)

    client = InfraiHttpClient("test-key")
    client.post = fake_post
    service = FaqSuggestionService(client, lambda text: [0.1, 0.2])
    service.ingest(FaqEntry("a", "How do I add captions?", "Upload an SRT track.", "creator-7"))
    suggestions = service.suggest("captions")

    assert suggestions[0].faq_id == "a"
    assert suggestions[0].answer == "Upload an SRT track."
    assert calls[1][1]["embedding"] == [0.1, 0.2]
    assert calls[2][1]["candidates"] == ["How do I add captions?"]
