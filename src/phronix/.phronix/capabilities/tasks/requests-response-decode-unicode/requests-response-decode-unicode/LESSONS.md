# Lessons — requests-response-decode-unicode

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — iter_content decode_unicode does not convert bytes to str

When using iter_content with decode_unicode=True, the returned chunks are still bytes, contrary to expectation that they would be str. Adding a comment to decode streamed chunks does not change this behavior. The test expects all chunks to be str, but they remain bytes, causing failure.

## Lessons
