def register(mcp):
    import pathlib, re
    file_path = pathlib.Path('requests/cookies.py')
    text = file_path.read_text(encoding='utf-8')
    # Ensure import of MutableMapping
    if 'from collections.abc import MutableMapping' not in text:
        # add after import collections line
        text = re.sub(r'(import collections)', r'\1\nfrom collections.abc import MutableMapping', text)
    # replace inheritance
    text = re.sub(r'collections\.MutableMapping', 'MutableMapping', text)
    file_path.write_text(text, encoding='utf-8')
    return {"status":"patched"}
