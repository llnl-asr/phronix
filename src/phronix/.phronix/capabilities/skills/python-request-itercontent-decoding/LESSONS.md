# Lessons — python-request-itercontent-decoding

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — IterContent may return bytes even with decode_unicode=True when fetching JSON

**2026-08-31** — When using `requests.Response.iter_content(chunk_size, decode_unicode=True)` on an `application/json` payload, the returned chunks are still `bytes` rather than `str`. This occurs because `iter_content` works on the raw response stream and does not apply the response encoding conversion that `.text` does. The `.text` attribute decodes the content according to the response's charset (or defaults to UTF-8), yielding a Unicode string. `iter_content` returns raw bytes unless `decode_unicode=True` and the underlying response is not using chunked transfer encoding; for JSON payloads, it's safer to use `response.json()` to get a parsed Python object, or decode the bytes manually with `.decode(response.encoding or 'utf-8')`.

**Why:** The misunderstanding that `iter_content(..., decode_unicode=True)` always returns Unicode strings can lead to type errors when processing binary JSON data, causing failures in scripts expecting strings.

**How to apply:**
- For JSON responses, prefer `response.json()` to directly obtain a Python dict/list.
- If you need to stream and decode, ensure `chunk_size` is small (e.g., 1) or manually decode each chunk: `for chunk in response.iter_content(chunk_size=1024, decode_unicode=True): text = chunk.decode(response.encoding or 'utf-8')`.
- Verify the type of each chunk before processing to avoid TypeError.

**Reference:** See Requests documentation for `Response.iter_content` and its `decode_unicode` parameter behavior on different content encodings.

**Why recorded:** The previous attempt incorrectly assumed that `decode_unicode=True` on `iter_content` yields a Unicode string for any content type, leading to a failure. Documenting this nuance prevents repeat attempts and guides future implementations.

### L2 — When using `requests

**2026-08-31** — When using `requests.Response.iter_content(chunk_size, decode_unicode=True)` on an `application/json` payload, the returned chunks may still be of type `bytes`. This is because `iter_content` provides raw data chunks; the `decode_unicode=True` flag only decodes bytes to `str` if the underlying response's encoding is known, but JSON content is often delivered as bytes and may not be automatically decoded. Therefore, it's safer to use `response.json()` for JSON payloads, or decode each byte chunk manually using `chunk.decode(response.encoding or 'utf-8')` before processing. Failure to account for this leads to TypeErrors and broken processing in tasks that stream JSON responses.

**Why recorded:** The previous attempt failed due to assuming `iter_content` returns strings for JSON data, causing a type error and preventing the task from succeeding. This lesson records that pitfall and instructs proper handling to avoid repeating the mistake.

**How to apply:**
- Use `response.json()` to parse JSON responses directly.
- If streaming is necessary, read chunks with `iter_content` and decode them explicitly: `for chunk in response.iter_content(chunk_size=1024, decode_unicode=True): data = chunk.decode(response.encoding or 'utf-8')`.
- Validate the type of each chunk before further processing.
- Update any existing code that expects string chunks from JSON iter_content to perform the explicit decode.
