---
name: psf-requests-3362
description: The psf-request-3362 subject.
subject: psf-requests-3362
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Parse response body correctly |
| `I2` | Instructions | Use r.text or r.json for response content |
| `I3` | Instructions | Problem description |
| `R1` | Rules | Do not assume iter_content returns text |
| `R2` | Rules | Key idea |






## Instructions

### I1 — Parse response body correctly

When using requests to fetch JSON or text data, do not rely on `Response.iter_content(decode_unicode=True)` to return a string. It yields raw bytes; you must decode them using the appropriate charset, e.g., `data = b''.join(r.iter_content(chunk_size=8192))` then `text = data.decode(r.encoding or 'utf-8')`. Alternatively, use `r.text` for UTF‑8 decoded content, or `r.json()` for JSON parsing.

### I2 — Use r.text or r.json for response content

When handling a `requests.Response`, prefer `response.text` for UTF‑8 decoded text or `response.json()` for JSON data. If you must use `iter_content`, concatenate the bytes and decode explicitly: `data = b''.join(response.iter_content(chunk_size=8192)); text = data.decode(response.encoding or 'utf-8')`.

### I3 — Problem description

When using requests, iter_content with decode_unicode=True returns chunks, not the full text, unlike r.text which returns the whole response as a string. This mismatch caused confusion in handling response bodies.

## Rules

### R1 — Do not assume iter_content returns text

If `decode_unicode=True` is set, `Response.iter_content` still yields bytes; you must explicitly decode each chunk (e.g., `chunk.decode(r.encoding or 'utf-8')`). Assuming it returns a string can cause type errors and failed patches.

### R2 — Key idea

`iter_content` yields an iterator of decoded string chunks; to obtain the full text you must join the chunks, e.g., `''.join(r.iter_content(..., decode_unicode=True))`. This is not equivalent to `r.text` which returns the entire response as a string.

## References

- `skill_load(name="psf-request-3362", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

