---
name: add-src-to-pythonpath
description: The add-src-to-pythonpath subject.
subject: add-src-to-pythonpath
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add repository src directory to Python import path |


## Instructions

### I1 — Add repository src directory to Python import path

Create a file `sitecustomize.py` at the repository root with the following content:
```python
import os
import sys

repo_root = os.path.abspath(os.path.dirname(__file__))
src_path = os.path.join(repo_root, "src")
if os.path.isdir(src_path) and src_path not in sys.path:
    sys.path.insert(0, src_path)
```
This ensures that when Python starts, the repository's `src` directory is added to the front of `sys.path`, allowing imports of the local Flask package.

Symptom:
- ImportError: cannot import name 'request_ctx' from 'flask.globals' during pytest collection.

Root cause:
- The repository's `src` directory was not on `sys.path`, causing Python to import an older Flask copy from a previous task's temporary directory, which lacked `request_ctx`.

Exact fix:
- Add the `sitecustomize.py` file as described.

## Rules

## References
