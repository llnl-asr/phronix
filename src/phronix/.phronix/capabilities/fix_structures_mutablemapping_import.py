def register(mcp):
    import pathlib, re
    file_path = pathlib.Path('requests/structures.py')
    text = file_path.read_text(encoding='utf-8')
    # add import if missing
    if 'from collections.abc import MutableMapping' not in text:
        text = text.replace('import collections', 'import collections\nfrom collections.abc import MutableMapping')
    # replace usage
    text = re.sub(r'collections\.MutableMapping', 'MutableMapping', text)
    file_path.write_text(text, encoding='utf-8')
    return {"status": "patched"}
