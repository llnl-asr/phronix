---
name: ignore-list-regex-search
description: Use `search` instead of `match` for ignore-list regexes to allow matching anywhere in the file path.
metadata:
  type: feedback
---

Directive: Change `_is_in_ignore_list_re` to use `file_pattern.search(element)` rather than `file_pattern.match(element)`.\nWhy: `match` only matches at the start, causing ignore patterns like `^src/gen/.*$` to miss paths not starting at the root; `search` ensures the pattern can appear anywhere within the path.
