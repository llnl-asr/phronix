---
name: psf-requests-3362
description: Fix misunderstanding of requests.Response.iter_content with decode_unicode=True returning bytes, not strings.
subject: psf-requests-3362
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I3` | Instructions | The patch that made the tests pass |
| `I4` | Instructions | Use iter_lines for text streaming |
| `I5` | Instructions | Decode iter_content chunks manually |
| `I6` | Instructions | Problem description |
| `I7` | Instructions | Key idea |
| `R1` | Rules | Do not assume iter_content yields str |
| `R2` | Rules | Do not modify test files |
| `R3` | Rules | What has been achieved so far, and what has not |



## Instructions

### I3 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/requests/cookies.py b/requests/cookies.py
index eee5168f..74327f5e 100755
--- a/requests/cookies.py
+++ b/requests/cookies.py
@@ -10,6 +10,7 @@ import copy
 import time
 import calendar
 import collections
+from collections.abc import MutableMapping
 from .compat import cookielib, urlparse, urlunparse, Morsel
 
 try:
@@ -161,7 +162,7 @@ class CookieConflictError(RuntimeError):
     Use .get and .set and include domain and path args in order to be more specific."""
 
 
-class RequestsCookieJar(cookielib.CookieJar, collections.MutableMapping):
+class RequestsCookieJar(cookielib.CookieJar, MutableMapping):
     """Compatibility class; is a cookielib.CookieJar, but exposes a dict
     interface.
 
diff --git a/requests/models.py b/requests/models.py
index fbb3c7e6..c0bcd5ad 100755
--- a/requests/models.py
+++ b/requests/models.py
@@ -695,8 +695,13 @@ class Response(object):
         chunks = reused_chunks if self._content_consumed else stream_chunks
 
         if decode_unicode:
-            chunks = stream_decode_response_unicode(chunks, self)
-
+            # Decode each chunk to unicode using the response's encoding or utf-8 fallback.
+            encoding = self.encoding or 'utf-8'
+            def decode_chunk(chunk):
+                if isinstance(chunk, (bytes, bytearray)):
+                    return chunk.decode(encoding, errors='replace')
+                return chunk
+            chunks = (decode_chunk(c) for c in chunks)
         return chunks
 
     def iter_lines(self, chunk_size=ITER_CHUNK_SIZE, decode_unicode=None, delimiter=None):
diff --git a/requests/packages/urllib3/_collections.py b/requests/packages/urllib3/_collections.py
index 77cee017..ab34ace2 100755
--- a/requests/packages/urllib3/_collections.py
+++ b/requests/packages/urllib3/_collections.py
@@ -1,5 +1,5 @@
 from __future__ import absolute_import
-from collections import Mapping, MutableMapping
+from collections.abc import Mapping, MutableMapping
 try:
     from threading import RLock
 except ImportError:  # Platform-specific: No threads available
diff --git a/requests/sessions.py b/requests/sessions.py
index 3f405ba9..cb02ef8d 100755
--- a/requests/sessions.py
+++ b/requests/sessions.py
@@ -9,7 +9,7 @@ requests (cookies, auth, proxies).
 
 """
 import os
-from collections import Mapping
+from collections.abc import Mapping
 from datetime import datetime
 
 from .auth import _basic_auth_str
diff --git a/requests/structures.py b/requests/structures.py
index 991056e4..615628cb 100755
--- a/requests/structures.py
+++ b/requests/structures.py
@@ -9,16 +9,17 @@ Data structures that power Requests.
 """
 
 import collections
+from collections.abc import MutableMapping
 
 from .compat import OrderedDict
 
 
-class CaseInsensitiveDict(collections.MutableMapping):
+class CaseInsensitiveDict(MutableMapping):
     """
     A case-insensitive ``dict``-like object.
 
     Implements all methods and operations of
-    ``collections.MutableMapping`` as well as dict's ``copy``. Also
+    ``MutableMapping`` as well as dict's ``copy``. Also
     provides ``lower_items``.
 
     All keys are expected to be strings. The structure remembers the
```

### I4 — Use iter_lines for text streaming

Replace uses of `Response.iter_content(..., decode_unicode=True)` with `Response.iter_lines(decode_unicode=True)` when you need a stream of Unicode strings. `iter_lines` returns each line as a ``bytes`` object; decode each line using `line.decode(response.encoding or 'utf-8')` if a string is required.

Example replacement:
```python
# Old
for chunk in r.iter_content(chunk_size=1024, decode_unicode=True):
    process(chunk)
# New
for line in r.iter_lines(decode_unicode=True):
    process(line.encode('utf-8') if isinstance(line, str) else line)
```
This ensures the data type matches the expectation of the surrounding code without altering the test suite.

### I5 — Decode iter_content chunks manually

If you must continue to use `Response.iter_content(..., decode_unicode=True)`, ensure each chunk is decoded to a string before use. For example:

```python
for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
    if isinstance(chunk, bytes):
        text = chunk.decode(response.encoding or 'utf-8', errors='replace')
    else:
        text = chunk
    # process text
```

This maintains compatibility with code that expects string data from the iterator while preserving the original call semantics. Use this approach only if you cannot switch to `iter_lines`.

### I6 — Problem description

A failing test `test_response_decode_unicode` expects `Response.iter_content(..., decode_unicode=True)` to yield strings, but the current `requests` version returns bytes.

### I7 — Key idea

`Response.iter_content(..., decode_unicode=True)` returns bytes in this version of `requests`; the fix requires overriding or wrapping `iter_content` to decode bytes to strings.

## Rules

### R1 — Do not assume iter_content yields str

Never treat chunks from `iter_content` as strings without decoding; they may be bytes.

### R2 — Do not modify test files

Only change source code; tests must remain untouched.

### R3 — What has been achieved so far, and what has not

**Already passing (1 of 1).** Do not rewrite the code that makes these pass — they are the part that works:
- `tests/test_requests.py::TestRequests::test_response_decode_unicode`

Measured after try 4.
