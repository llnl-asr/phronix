---
name: psf-requests-2148
description: Fix uncaught socket.error in requests usage
subject: psf-requests-2148
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem |
| `I2` | Instructions | Naming |
| `I3` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — Problem

Raw socket errors from the requests library bubble up as socket.error instead of being wrapped in requests.exceptions.ConnectionError, causing uncaught exceptions in client code.

### I2 — Naming

Use a concise, kebab-case skill name that reflects the problem, e.g., `psf-requests-2148`. This allows later runs to load the skill directly via `skill_load("psf-requests-2148")`.

### I3 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/requests/models.py b/requests/models.py
index 0dc5556..7525ea9 100755
--- a/requests/models.py
+++ b/requests/models.py
@@ -22,7 +22,8 @@ from .packages.urllib3.util import parse_url
 from .packages.urllib3.exceptions import DecodeError
 from .exceptions import (
     HTTPError, RequestException, MissingSchema, InvalidURL,
-    ChunkedEncodingError, ContentDecodingError)
+    ChunkedEncodingError, ContentDecodingError, ConnectionError)
+import socket
 from .utils import (
     guess_filename, get_auth_from_url, requote_uri,
     stream_decode_response_unicode, to_key_val_list, parse_header_links,
@@ -640,6 +641,8 @@ class Response(object):
                     raise ChunkedEncodingError(e)
                 except DecodeError as e:
                     raise ContentDecodingError(e)
+                except socket.error as e:
+                    raise ConnectionError(str(e))
             except AttributeError:
                 # Standard file-like object.
                 while True:
```

## Rules
