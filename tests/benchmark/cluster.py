"""The LLM cluster's own config, read rather than restated.

`tuolumne-llm/cluster.json` is written by whatever brought the cluster up: which
hosts, which GPUs, which ports, the gateway in front of them, and the key it
expects. That file is the truth, and every other copy of those facts is a copy
that will be wrong the next time the cluster moves.

So nothing here is hard-coded. Point the benchmark at the file and it derives
the endpoint, the credential and the model name from it.

Two ways to reach the same GPUs:

* **The gateway** — one URL, and it load-balances across every backend. This is
  the default, because a client that talks to one URL cannot get the balancing
  wrong, and the gateway is the thing that knows which backends are alive.
* **The backends** — the individual ``llama-server`` ports. Useful when the
  gateway is down, and useful when we want *affinity*: llama.cpp caches the
  prompt prefix per server, so pinning a task to one backend keeps its
  conversation warm instead of re-prefilling ~185k tokens on a fresh host.
"""
from __future__ import annotations

import hashlib
import threading
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

def _tuned(key: str, fallback):
    """A tuning value, falling back to what the code shipped with.

    Configuration lives in one file. It used to live here as constants, and a
    probe-then-cap written as two steps let the first shadow the second — the
    cap never applied and nobody could see why from either place.
    """
    try:
        from phronix.tuning import get

        return get(key, fallback)
    except Exception:
        return fallback


#: Where the cluster writes itself, when nobody says otherwise.
DEFAULT_CONFIG = Path("/usr/workspace/haridev/phronix/tuolumne-llm/cluster.json")


class ClusterConfig:
    """One cluster, as its config file describes it."""

    def __init__(self, data: Dict[str, Any], source: Optional[Path] = None) -> None:
        #: Backend assigned per key, and the position to deal from next.
        #
        # Kept on the instance rather than globally so two configs — a run and a
        # probe, say — cannot deal from each other's counter.
        self._assigned: Dict[str, str] = {}
        self._assign_next = 0
        self._assign_lock = threading.Lock()
        self.data = data or {}
        self.source = source

    # -- loading -----------------------------------------------------------

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "ClusterConfig":
        """Read the config, raising with the path when it is not there.

        A missing cluster file is worth failing loudly on: the alternative is a
        run that quietly falls back to a default endpoint and reports numbers
        for hardware nobody meant to measure.
        """
        target = Path(path or DEFAULT_CONFIG)
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise FileNotFoundError(
                f"no cluster config at {target}. Start the cluster, or pass "
                f"--cluster with the path to its cluster.json.") from None
        except ValueError as exc:
            raise ValueError(f"{target} is not valid JSON: {exc}") from None
        if not isinstance(data, dict):
            raise ValueError(f"{target} does not describe a cluster")
        return cls(data, target)

    # -- what a client needs ----------------------------------------------

    @property
    def model(self) -> str:
        """The default model to ask for. The alias is what servers answer to."""
        listed = self.models
        if listed:
            return listed[0]
        return str(self.data.get("alias") or self.data.get("model") or "")

    @property
    def models(self) -> List[str]:
        """Every model the fleet serves, in the order it was deployed.

        A mixture fleet puts different models on different nodes behind one
        gateway, so "which model" becomes a per-request choice rather than a
        property of the endpoint. Read from the config because a mixture that is
        not recorded is one the benchmark cannot use.
        """
        listed = self.data.get("models")
        if isinstance(listed, list) and listed:
            # Deduplicated, order kept. A fleet serving one model on four GPUs
            # records it four times, and a roster of duplicates is not a
            # mixture: it made the aspect fan-out think it was spreading across
            # models and label every trace line `@gpt-oss-120b`, which is noise
            # when there is only one model to name.
            seen, unique = set(), []
            for name in (str(m) for m in listed if m):
                if name not in seen:
                    seen.add(name)
                    unique.append(name)
            return unique
        single = str(self.data.get("alias") or self.data.get("model") or "")
        return [single] if single else []

    @property
    def api_key(self) -> str:
        return str((self.data.get("gateway") or {}).get("key") or "")

    @property
    def gateway_url(self) -> str:
        """The one URL, or empty when the config has no gateway."""
        gateway = self.data.get("gateway") or {}
        host, port = gateway.get("host"), gateway.get("port")
        if not host or not port:
            return ""
        return f"http://{host}:{port}/v1"

    def backend_urls(self) -> List[str]:
        """Every backend, in config order.

        Order is kept rather than sorted: it is host-major, so consecutive
        entries are different GPUs of the same node. Anything assigning work
        round-robin therefore spreads across GPUs before it doubles up on a
        host, which is what we want when hosts are the scarcer resource.
        """
        out: List[str] = []
        for server in self.data.get("servers") or []:
            host, port = server.get("host"), server.get("port")
            if host and port:
                out.append(f"http://{host}:{port}/v1")
        return out

    def pinned_models(self) -> List[str]:
        """Model aliases that each resolve to exactly ONE backend.

        The gateway serves every backend twice: once under the shared name,
        which load-balances, and once under `name@N`, which does not. Asking for
        a pinned alias is how a client stays on one server.
        """
        # The GATEWAY first, the file only as a fallback.
        #
        # This read the file first, which contradicts the reasoning below and
        # cost a live run. `deploy.sh` numbers the aliases `@0..@N` from the
        # host x GPU loop it INTENDS to launch, and writes them before knowing
        # what came up: asked for 8 nodes x 4 GPUs it wrote @0..@31 while 23
        # servers ever registered, so nine aliases named nothing from the start.
        #
        # Every agent that asked for one got
        # `400: anthropic_messages: Invalid model name passed in`, once per
        # fanned-out agent, for the whole run. Removing entries afterwards makes
        # it worse rather than better: the survivors keep their original numbers,
        # so the list gains holes and a client counting `@0..@22` still lands in
        # one. A count is not a list, and only the gateway knows which numbers
        # exist.
        served = self._aliases_from_gateway()
        if served:
            return served
        listed = self.data.get("pinned_models")
        if isinstance(listed, list) and listed:
            return [str(m) for m in listed if m]
        return []

    def _aliases_from_gateway(self) -> List[str]:
        """The pinned aliases the gateway is serving right now, or [].

        The aliases exist on the gateway whether or not the deploy managed to
        record them — measured once with all 32 served and the key missing from
        cluster.json, which would have silently turned affinity off and cost
        half the fleet's GPU time to re-prefill. What is deployed is the
        authority; the file is a convenience.

        Returns [] on any failure, so an unreachable gateway falls back to the
        file rather than turning affinity off.
        """
        import json as _json
        import urllib.request

        gateway = self.gateway_url
        if not gateway:
            return []
        request = urllib.request.Request(f"{gateway.rstrip('/')}/models")
        if self.api_key:
            request.add_header("Authorization", f"Bearer {self.api_key}")
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                served = [str(m.get("id") or "")
                          for m in _json.loads(response.read()).get("data", [])]
        except Exception:
            return []
        # `name@N` is the pinned form; the bare name load-balances.
        return sorted((m for m in served if "@" in m),
                      key=lambda m: int(m.rsplit("@", 1)[1])
                      if m.rsplit("@", 1)[1].isdigit() else 0)

    def model_for(self, key: str) -> str:
        """The model a given task should ask for, so its turns stay together.

        An agent re-sends its whole conversation every turn, and llama.cpp
        caches that history per server — so a turn landing on a different
        backend re-processes everything. Measured on the load-balanced fleet:
        189,193,540 prompt tokens against 5,228,544 generated, prefill costing
        more GPU time than decode. A repeat to the same backend reported 82 of
        87 prompt tokens cached; scattered, 0.

        Round-robin, then REMEMBERED — which keeps the stability a hash gave
        without its collisions.

        Hashing was stable but blind to what it had already handed out: keys
        collide, so with 30 tasks over 24 backends some servers took three while
        others took none. Under the `solo` profile a backend has ONE slot, so a
        third task on a server is a third task queued while a neighbour idles —
        which is most of what the deferred count measures.

        Dealing in order and remembering the choice gives the same guarantees
        for free: a retry of the same task returns to the backend still holding
        its history, and two arms of one task share a backend and its warm
        prefix, because both ask with the same key. What changes is that the
        (n+1)th distinct key goes to the emptiest server rather than to whichever
        one its digest happened to name.
        """
        pinned = self.pinned_models()
        if not pinned:
            return self.model
        key = str(key)
        with self._assign_lock:
            chosen = self._assigned.get(key)
            if chosen is None or chosen not in pinned:
                chosen = pinned[self._assign_next % len(pinned)]
                self._assign_next += 1
                self._assigned[key] = chosen
            return chosen

    def endpoints(self, direct: bool = False) -> List[str]:
        """The URLs to use: the gateway, or every backend when *direct*."""
        if direct:
            backends = self.backend_urls()
            if backends:
                return backends
        gateway = self.gateway_url
        return [gateway] if gateway else self.backend_urls()

    # -- description -------------------------------------------------------

    def server_context(self, timeout: int = 8) -> int:
        """The per-slot context a backend actually offers, or 0 if unreachable.

        Read from `/props`, which reports the window a single request may use —
        already divided by `--parallel`. That division is why this is probed
        rather than computed: the client cannot see the launch flags, and the
        total context in them is not what any one request gets.
        """
        import json as _json
        import urllib.request

        for url in self.backend_urls()[:3]:
            root = url[:-3].rstrip("/") if url.endswith("/v1") else url
            try:
                with urllib.request.urlopen(f"{root}/props", timeout=timeout) as r:
                    data = _json.loads(r.read())
            except Exception:
                continue
            window = (data.get("default_generation_settings") or {}).get("n_ctx")
            if window:
                return int(window)
        return 0

    #: Slots one task unit occupies on average. See `llm.duty_cycle`.
    DUTY_CYCLE = _tuned("llm.duty_cycle", 0.53)

    def capacity(self, timeout: int = 8) -> int:
        """Concurrent requests the fleet can serve: servers x slots each.

        Probed rather than assumed. `--parallel` is a launch flag the client
        cannot see, and it is the number that decides whether a run saturates
        the fleet or leaves three quarters of it idle.
        """
        import json as _json
        import urllib.request

        servers = self.data.get("servers") or []
        if not servers:
            return 0
        slots = 0
        for url in self.backend_urls()[:3]:
            root = url[:-3].rstrip("/") if url.endswith("/v1") else url
            try:
                with urllib.request.urlopen(f"{root}/props", timeout=timeout) as r:
                    slots = int(_json.loads(r.read()).get("total_slots") or 0)
            except Exception:
                continue
            if slots:
                break
        return len(servers) * (slots or 1)

    def tasks_to_fill(self, arms: int = 2) -> int:
        """Concurrent TASKS needed to keep the fleet busy.

        Not a target to hit at any cost: spare capacity is only waste when work
        is waiting on it, and a run with nothing deferred is not being held up.
        It is the number that says whether a fleet this size was worth having
        for this workload.
        """
        total = self.capacity()
        if not total:
            return 0
        return max(1, round(total / (self.DUTY_CYCLE * max(1, arms))))

    def describe(self) -> str:
        servers = self.data.get("servers") or []
        hosts = {s.get("host") for s in servers if s.get("host")}
        gateway = self.gateway_url or "(none)"
        return (f"{self.model} on {len(servers)} server(s) across "
                f"{len(hosts)} host(s), gateway {gateway}")


def load(path: Optional[Path] = None) -> ClusterConfig:
    return ClusterConfig.load(path)


#: opencode reads providers from here. NOT `~/.opencode/` — that path exists,
#: opencode logs it as "loading", and a provider written there is silently
#: ignored, which cost an afternoon once.
OPENCODE_CONFIG = Path.home() / ".config" / "opencode" / "opencode.jsonc"

#: The provider name the arms ask for: `--model <PROVIDER_NAME>/<alias>`.
PROVIDER_NAME = "tuolumne"

#: Working context, regardless of how much the servers offer. See
#: `llm.context_cap` in tuning.yaml for what it is and why.
CONTEXT_CAP = _tuned("llm.context_cap", 65536)


def configure_opencode(cluster: ClusterConfig, direct: bool = False,
                       path: Optional[Path] = None) -> Dict[str, Any]:
    """Write the cluster into opencode's provider config.

    Generated from ``cluster.json`` rather than hand-edited, because the hosts
    and ports change every time the cluster is rebuilt and a stale provider
    fails as a connection error at the first API call of the first task.

    Only this provider is touched; anything else already in the file is kept.
    The benchmark's private HOMEs symlink `.config`, so one write here reaches
    every agent invocation.
    """
    import re

    target = Path(path or OPENCODE_CONFIG)
    existing: Dict[str, Any] = {}
    if target.is_file():
        raw = target.read_text(encoding="utf-8")
        try:
            # The file is JSONC by name and convention; strip line comments.
            existing = json.loads(re.sub(r"^\s*//.*$", "", raw, flags=re.M))
        except ValueError:
            existing = {}
    if not isinstance(existing, dict):
        existing = {}

    urls = cluster.endpoints(direct=direct)
    if not urls:
        raise ValueError(f"{cluster.source} names no gateway and no servers")

    existing.setdefault("$schema", "https://opencode.ai/config.json")
    existing.setdefault("provider", {})
    # Declaring the model's limits is not optional.
    #
    # Without them opencode assumes a default context of 32768 and sizes its
    # request to fit: a 28,652-token prompt left 4,116 tokens of output, the
    # step ended with `"reason": "length"`, and the agent stopped after two
    # steps having written nothing. Every task failed as "agent produced no
    # patch", which reads as a model that cannot do the work rather than one
    # that was never allowed to finish a sentence.
    #
    # The servers are configured far larger than this (2,048,000 per slot), so
    # these are deliberately conservative: big enough that a long agent
    # conversation is never truncated, small enough that one runaway request
    # cannot monopolise a slot's KV.
    # The working window: never more than the server holds, never more than the
    # model is fast and accurate in.
    #
    # Two ceilings, and both matter. The SERVER's is a hard limit — `-c` is
    # divided by `--parallel`, so the per-slot window is a fraction of the
    # launch flag and is written down nowhere the client can see. Exceeding it
    # ends a request with `"reason": "length"` mid-sentence, and every task then
    # fails as "agent produced no patch", which reads as a model too weak for
    # the work rather than one cut off in the middle of it.
    #
    # OURS is a quality and speed limit. Conversations that reached 155,548
    # tokens produced worse results, and decode collapses as context grows —
    # measured across one fleet at one moment: 96,900 tokens gave 107 tok/s,
    # 104,724 gave 42, 113,055 gave 25.
    #
    # An explicit `limits.context` in cluster.json overrides both, for a
    # deployment that knows better than either default.
    limits = cluster.data.get("limits") or {}
    window = int(limits.get("context") or 0)
    if not window:
        probed = cluster.server_context()
        window = min(probed, CONTEXT_CAP) if probed else CONTEXT_CAP

    models = {
        name: {
            "name": name,
            "limit": {"context": window,
                      "output": int(limits.get("output")
                                    or _tuned("llm.output_cap", 32000))},
        }
        for name in cluster.models
    }
    existing["provider"][PROVIDER_NAME] = {
        "npm": "@ai-sdk/openai-compatible",
        "name": f"tuolumne cluster ({', '.join(cluster.models)})",
        "options": {"baseURL": urls[0], "apiKey": cluster.api_key},
        "models": models,
    }

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    return {"file": str(target), "provider": PROVIDER_NAME,
            "base_url": urls[0], "model": cluster.model,
            "qualified": f"{PROVIDER_NAME}/{cluster.model}"}
