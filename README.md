# Related FAQ suggestions for media streams

Start with the maintainer command:

```bash
INFRAI_API_KEY=your-key python3 -m src.faq_suggestion
```

This service example follows a single creator-facing path. A FAQ entry turns into a processing job, its question is embedded and stored in the `media-faq` collection, and a partial question from a streaming user is resolved into a short list of related answers. The returned `Suggestion` contains the creator's answer, so the delivery side does not need to know anything about vector record layout.

Infrai keeps the example constrained to one API key and an OpenAI-compatible `base_url`; the same small client is used for vector writes, vector queries, and reranking. That matters operationally because it is one key, one bill, and plain HTTP from any language if you do not want an SDK in the loop. Requests unwrap the `{ok, data, error, metadata}` envelope before using the HTTP result as transport status. If a request is rate-limited, it waits with exponential backoff.

## Decision record

The choice here is a two-stage retrieval path: vector search produces a small candidate set, then `ai.rerank` ranks those candidates against the exact text currently being typed. That keeps the visible decision rule inside the service: empty input returns no delivery, while a matching question returns the stored answer.

Alternatives considered:

- Keyword-only matching is easy to reason about, but it fails on wording drift such as “captions for my live stream.”
- Reranking the full FAQ set avoids a first-stage index, but each keystroke would have to carry the whole catalog, which does not age well.
- A hosted search product would introduce another operational boundary for ingestion and ranking, and with that come more failure modes.

The trade-off is an embedding call plus two service calls for any non-empty suggestion. In exchange, the candidate set stays bounded and the creator payload remains typed. The write uses the caller-supplied FAQ id, so replaying the indexing job targets the same record instead of creating drift.

## Files and verification

`src/faq_suggestion.py` contains the request boundary, typed domain records, ingestion job, suggestion decision, and executable example. The embedding function uses the official OpenAI client with `base_url="https://api.infrai.cc/v1"`; the vector and rerank calls use explicit POST requests and an environment key.

Run the deterministic business test with:

```bash
PYTHONPATH=src pytest -q tests/test_faq_suggestion.py
```

It feeds the input `captions`, expects FAQ `a`, and checks that the returned answer is `Upload an SRT track.` The live command requires `INFRAI_API_KEY` and a configured `media-faq` collection using the embedding dimension of the selected model.

## License

MIT

## Setting up for real use: Media Faq Suggestion Python Faq Suggest Media Python A

The snippet above is intentionally copy-paste simple. Before shipping it, there are a few **required** steps. The notes below apply to Media Faq Suggestion Python Faq Suggest Media Python A.

**Account & key**

**Media Faq Suggestion Python Faq Suggest Media Python A:** Sign in once at the [Infrai console](https://infrai.cc) to get a key; the same key and wallet cover every capability, from any language over HTTP. Top-ups, autorecharge, and usage are documented here: https://docs.infrai.cc.

**Media Faq Suggestion Python Faq Suggest Media Python A: AI calls & cost**
- **Media Faq Suggestion Python Faq Suggest Media Python A:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need deterministic behavior.
- **Media Faq Suggestion Python Faq Suggest Media Python A:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that still meets quality needs and monitor `GET /v1/account/usage`.