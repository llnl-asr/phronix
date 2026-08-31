def register(mcp):
    import time
    import logging
    
    @mcp.tool()
    def rebuild_graph(max_retries: int = 5, backoff_factor: float = 2.0, alert_threshold: int = 3):
        """Attempts to rebuild the knowledge graph.
        Retries with exponential backoff up to `max_retries` times.
        If the number of consecutive failures reaches `alert_threshold`, logs an alert.
        Returns a dict with keys: 'attempts', 'success', 'last_error'."""
        attempts = 0
        success = False
        last_error = None
        while attempts < max_retries:
            attempts += 1
            try:
                # Use the built‑in tool to rebuild the graph.
                result = mcp.graph_ensure(scope="knowledge")
                # Assume success if no exception raised.
                success = True
                break
            except Exception as e:
                last_error = str(e)
                logging.error(f"Graph rebuild attempt {attempts} failed: {e}")
                if attempts >= alert_threshold:
                    logging.warning(f"Alert: graph rebuild has failed {attempts} times")
                # exponential backoff
                sleep_time = backoff_factor ** (attempts - 1)
                time.sleep(sleep_time)
        return {"attempts": attempts, "success": success, "last_error": last_error}
