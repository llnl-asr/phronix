# Lessons — sphinx-doc-sphinx-8721

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — P1 - startswith too broad

Using startswith('epub') matches 'epub3' and any builder name starting with 'epub', which is too broad and doesn't properly respect the viewcode_enable_epub setting.

### P2 — P2 - Config not integrated

The fix must include the viewcode_enable_epub config check. Just changing startswith to in {'epub'} without the config check won't fix the default case.

### P3 — P3 - Test regression

Must ensure test_viewcode_epub_enabled still passes after the fix (it tests epub build with viewcode_enable_epub=True).

## Lessons
