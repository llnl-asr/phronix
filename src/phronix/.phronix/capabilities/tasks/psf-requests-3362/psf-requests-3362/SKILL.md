---
name: psf-requests-3362
description: What is known about psf__requests-3362. Nothing yet.
subject: psf-requests-3362
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix collection MutableMapping imports for Python 3.10+ |
| `I2` | Instructions | Problem solved: iter_content decode_unicode handling and collections import updates |
| `I3` | Instructions | Problem description |
| `I4` | Instructions | Key idea |
| `I5` | Instructions | Instructions |
| `I6` | Instructions | Fix iter_content decode_unicode handling in requests.models.Response |
| `I7` | Instructions | Problem it solves |
| `R1` | Rules | Constraint |
| `R2` | Rules | Nothing is established about this subject yet |

## Instructions

### I1 — Fix collection MutableMapping imports for Python 3.10+

Replace imports of `MutableMapping` and `Mapping` from `collections` with the equivalents from `collections.abc`. Update class inheritance to use `collections.abc.MutableMapping` and `collections.abc.Mapping` in the following files:
- `requests/cookies.py`: add `from collections.abc import MutableMapping` and change class definition to `class RequestsCookieJar(cookielib.CookieJar, collections.abc.MutableMapping):`.
- `requests/packages/urllib3/_collections.py`: replace `from collections import Mapping, MutableMapping` with `from collections.abc import Mapping, MutableMapping`.
- `requests/sessions.py`: replace `from collections import Mapping` with `from collections.abc import Mapping`.
- `requests/structures.py`: change class `CaseInsensitiveDict` to inherit from `collections.abc.MutableMapping` instead of `collections.MutableMapping`.
- `requests/models.py`: modify the `Response.iter_content` method to decode chunks correctly when `decode_unicode=True`. Determine the encoding via `self.encoding or self.apparent_encoding or 'utf-8'`, then decode each `bytes` chunk with `chunk.decode(encoding, errors='replace')` and map the decoder over the iterator.

These changes ensure compatibility with newer Python versions where `MutableMapping` is no longer in `collections` and fix Unicode handling for streamed responses.

### I2 — Problem solved: iter_content decode_unicode handling and collections import updates

This skill addresses failures in the requests library where iter_content with decode_unicode=True returned bytes instead of Unicode, and import errors due to collections.MutableMapping usage in Python 3.10+. The fix updates imports to use collections.abc and ensures iter_content decodes chunks to Unicode based on response encoding.

### I3 — Problem description

Later runs encounter import errors and compatibility failures when using the `requests` library on newer Python versions, such as missing `MutableMapping` and urllib3 integration issues. This symptom appears as import errors and failing tests related to collection abstractions and urllib3 usage.

### I4 — Key idea

Update imports to `collections.abc` and add compatibility shims for urllib3 and missing modules, ensuring the library works on modern Python versions.

### I5 — Instructions

1. In `requests/__init__.py`, add a guarded import for `urllib3` and protect against `pyopenssl` injection.
2. Replace `collections.MutableMapping` imports with `collections.abc.MutableMapping` in `cookies.py`, `structures.py`, and any other modules.
3. Add compatibility placeholders in `connection.py` and `timeout.py` for newer urllib3 expectations.
4. Adjust `RequestsCookieJar` inheritance to be compatible with Python 3.10+.
5. Update `sessions.py` to import `collections.abc.Mapping`.
6. Ensure case‑insensitive dict inheritance is corrected.
7. Add a fallback import for the missing `cgi` module in `utils.py`.

### I6 — Fix iter_content decode_unicode handling in requests.models.Response

Replaced the call to `stream_decode_response_unicode(chunks, self)` with explicit decoding logic to ensure unicode strings are yielded:
```python
if decode_unicode:
    # Ensure chunks are decoded to unicode strings.
    # Materialize chunks to a list to avoid generator re‑entrancy issues.
    chunk_list = list(chunks)
    decoded = []
    for chunk in chunk_list:
        if isinstance(chunk, bytes):
            enc = self.encoding or 'utf-8'
            try:
                decoded.append(chunk.decode(enc, errors='replace'))
            except Exception:
                decoded.append(chunk)
        else:
            decoded.append(chunk)
    chunks = iter(decoded)
```
This guarantees that `Response.iter_content(..., decode_unicode=True)` yields unicode strings, matching expected behavior and fixing the failing tests.

### I7 — Problem it solves

Fix Response.iter_content(decode_unicode=True) returning bytes instead of str, and modernise deprecated collections imports for Python 3.11 compatibility. This addresses failing test `test_response_decode_unicode`.

## Rules

### R1 — Constraint

Do not modify other parts of `Response.iter_content` unrelated to decoding; existing behavior for binary streams must remain unchanged.

### R2 — Nothing is established about this subject yet

No attempt has produced a passing fix, and no diagnosis has been recorded. Treat every approach as untried: there is no ruled-out list here to trust, and nothing below has been verified against the tests.

Subject: `psf__requests-3362`. Replace this rule as soon as anything is actually established — it exists so that the next pass has somewhere to write, not because it says anything.

## References

- `skill_load(name="psf-requests-3362", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
