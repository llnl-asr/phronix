def register(mcp):
    import pathlib, re
    file_path = pathlib.Path('requests/sessions.py')
    text = file_path.read_text(encoding='utf-8')
    # ensure import from collections.abc
    if 'from collections.abc import Mapping' not in text:
        text = re.sub(r'from collections import Mapping', 'from collections.abc import Mapping', text)
    else:
        text = re.sub(r'from collections import Mapping', 'from collections.abc import Mapping', text)
    file_path.write_text(text, encoding='utf-8')
    return {"status": "patched"}
