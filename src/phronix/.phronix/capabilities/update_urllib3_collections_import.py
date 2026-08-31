def register(mcp):
    import pathlib, re
    file_path = pathlib.Path('requests/packages/urllib3/_collections.py')
    text = file_path.read_text(encoding='utf-8')
    new_text = re.sub(r'from collections import (Mapping, MutableMapping)',
                      r'from collections.abc import Mapping, MutableMapping', text)
    file_path.write_text(new_text, encoding='utf-8')
    return {"status": "patched"}
