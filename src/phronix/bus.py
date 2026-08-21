"""The learning bus: producers push events, one consumer pulls them by topic.

Every stage of every task reports what worked and what did not, and a learner
turns what repeats into skills and tools. The transport for that has three
awkward properties:

* **Producers are short-lived.** Each is an MCP tool call inside an agent
  subprocess that exists for one stage. It cannot hold a connection, retry over
  a session, or be told to shut down cleanly.
* **There are many of them at once.** Aspects, tuning workers and evaluators run
  concurrently, and tasks may too.
* **The consumer is not always there.** The learner starts with the first
  research pass and stops when the arm finishes; a run that never researches
  never starts one.

ZeroMQ suits the first two: a PUSH socket connects without a handshake, sends
without waiting for a peer, and closes without ceremony. It does not suit the
third — a PUSH with no PULL queues to a high-water mark and then blocks or
drops, and neither is acceptable for a producer whose only job is to not get in
the way.

So the bus is ZeroMQ with a file behind it. The socket carries the live stream;
the file is the record. A producer sends and appends, both non-blocking; a
consumer takes whichever it can. What that buys is the property the file alone
could not give and the socket alone could not either: an observation reported
while nobody was listening is still there when somebody starts.

The address is an ``ipc://`` endpoint under the layer's research directory,
because every producer and consumer in a run shares a filesystem and a host.
No port to allocate, nothing to reach over a network, and the endpoint is
discoverable from the same place the rest of the research lives.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

#: Overriding this points a run at its own bus, which is what keeps two
#: concurrent runs on one host from consuming each other's observations.
ENDPOINT_ENV = "PHRONIX_BUS"

def _tuned(key: str, fallback):
    """A tuning value, falling back to what the code shipped with."""
    try:
        from phronix.tuning import get

        return get(key, fallback)
    except Exception:
        return fallback


#: How long a producer will wait for the socket. Effectively zero: reporting is
#: a side effect of doing the work, and a stage that blocks on it has been made
#: slower by the thing meant to make everything faster.
SEND_TIMEOUT_MS = _tuned("bus.send_timeout_ms", 50)

#: How many unsent messages a producer will hold before giving up on the socket.
#: Small on purpose — the file behind the bus is what makes dropping safe.
SEND_HWM = _tuned("bus.send_high_water_mark", 1000)


def endpoint(root: Optional[Path] = None) -> str:
    """Where the bus lives for this run.

    An ``ipc://`` socket beside the research it is about. Every producer and
    consumer in a run is on one host, so a unix socket is the whole requirement
    — and unlike a TCP port it needs no allocation, cannot collide with another
    service, and disappears with the directory.
    """
    configured = os.environ.get(ENDPOINT_ENV, "").strip()
    if configured:
        return configured
    if root is None:
        from phronix.layers import resolve_write_layer

        root = Path(resolve_write_layer().root) / "research"
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    return f"ipc://{root / 'learning.sock'}"


def _context():
    """The process-wide ZeroMQ context, or None when pyzmq is absent.

    Absent is a supported state. The bus is an optimisation over the file, so a
    deployment without pyzmq keeps working — it simply learns on the file's
    cadence rather than the socket's.
    """
    try:
        import zmq
    except ImportError:
        return None

    global _CONTEXT
    if _CONTEXT is None:
        _CONTEXT = zmq.Context.instance()
    return _CONTEXT


_CONTEXT = None
_SENDER = None


def publish(topic: str, payload: Dict[str, Any],
            address: Optional[str] = None) -> bool:
    """Send one event. Never blocks, never raises, never waits for a consumer.

    Returns whether the socket took it. A false is not a failure the caller
    needs to handle — the caller has already written the event to the file, and
    that is the durable copy. It matters only to the consumer's latency: a
    dropped message is one the learner sees on its next file read instead of
    immediately.
    """
    context = _context()
    if context is None:
        return False

    import zmq

    global _SENDER
    try:
        if _SENDER is None:
            _SENDER = context.socket(zmq.PUSH)
            _SENDER.setsockopt(zmq.SNDHWM, SEND_HWM)
            # Do not hold the process open for unsent messages: a producer is a
            # stage that has finished, and a lingering socket makes it look hung.
            _SENDER.setsockopt(zmq.LINGER, 0)
            _SENDER.setsockopt(zmq.SNDTIMEO, SEND_TIMEOUT_MS)
            _SENDER.connect(address or endpoint())

        _SENDER.send_multipart([
            str(topic or "(none)").encode("utf-8"),
            json.dumps(payload).encode("utf-8"),
        ])
        return True
    except Exception:
        # Every failure here is the same failure: the consumer is not up, or the
        # queue is full. Both mean "the file will carry this one".
        return False


class Collector:
    """The consumer's end: bind, then drain whatever has arrived.

    Draining is non-blocking by design. The learner has two clocks — it notices
    every ten seconds and reconciles every minute — so it wants "everything
    waiting right now", not "block until something arrives". A consumer that
    blocked on the socket could not also be watching its own clock.
    """

    def __init__(self, address: Optional[str] = None) -> None:
        self.address = address or endpoint()
        self._socket = None
        context = _context()
        if context is None:
            return

        import zmq

        try:
            self._socket = context.socket(zmq.PULL)
            self._socket.setsockopt(zmq.RCVHWM, SEND_HWM)
            self._socket.setsockopt(zmq.LINGER, 0)
            self._socket.bind(self.address)
        except Exception:
            # Another consumer already holds the endpoint, or ipc is
            # unavailable. Either way this one reads the file instead, which is
            # the same information a little later.
            self._socket = None

    @property
    def live(self) -> bool:
        return self._socket is not None

    def drain(self, limit: int = 500) -> List[Dict[str, Any]]:
        """Everything queued right now, oldest first. Empty if nothing is."""
        if self._socket is None:
            return []

        import zmq

        taken: List[Dict[str, Any]] = []
        for _ in range(limit):
            try:
                topic, body = self._socket.recv_multipart(zmq.NOBLOCK)
            except zmq.Again:
                break
            except Exception:
                break
            try:
                event = json.loads(body.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                continue
            if isinstance(event, dict):
                event.setdefault("topic", topic.decode("utf-8", "replace"))
                event.setdefault("at", time.time())
                taken.append(event)
        return taken

    def close(self) -> None:
        if self._socket is not None:
            try:
                self._socket.close(linger=0)
            finally:
                self._socket = None
