def register(mcp):
    import socket
    from requests.models import Response
    from requests.exceptions import ConnectionError
    original_content = Response.content.fget
    def patched_content(self):
        if self._content is False:
            try:
                if self._content_consumed:
                    raise RuntimeError('The content for this response was already consumed')
                if self.status_code == 0:
                    self._content = None
                else:
                    try:
                        self._content = bytes().join(self.iter_content(CONTENT_CHUNK_SIZE)) or bytes()
                    except socket.error as exc:
                        raise ConnectionError(exc, request=self.request)
            except AttributeError:
                self._content = None
        self._content_consumed = True
        return self._content
    Response.content = property(patched_content)
