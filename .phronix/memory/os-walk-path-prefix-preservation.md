---
name: os-walk-path-prefix-preservation
description: os.walk() preserves input path prefix in all yielded paths
metadata:
  type: reference
---

**What It Is**: os.walk() preserves the exact prefix given to it in all yielded paths.

**Behavior**:
- `os.walk('./src')` yields: `'./src'`, `'./src/sub'`, `'./src/sub/deep'`
- `os.walk('src')` yields: `'src'`, `'src/sub'`, `'src/sub/deep'`
- `os.walk('/abs/path')` yields: `'/abs/path'`, `'/abs/path/sub'`

**Why This Matters**: When users run tools with relative paths like `.` or `./src`, the yielded paths contain those prefixes. If these paths are compared against regex patterns without normalization, patterns like `^src/.*$` won't match `./src/...`.

**Design Decision**: os.walk() behavior is by design - it preserves the input form. The responsibility for normalization lies with the caller when doing pattern matching.

**Common Pattern**: 
```python
for root, dirs, files in os.walk(start_path):
    normalized_root = os.path.normpath(root)
    # Use normalized_root for pattern matching
```

**Related**: [[defensive-path-normalization]]
