---
name: flask-routing-internals
description: How werkzeug/Flask store per-rule subdomain vs host, and how they relate to SERVER_NAME.
subject: flask-routing-internals
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | rule.subdomain vs rule.host are mutually exclusive by host_matching mode |
| `X1` | References | No built-in full-domain-per-rule resolver in werkzeug or Flask |



## Instructions

## Rules

### R1 — rule.subdomain vs rule.host are mutually exclusive by host_matching mode

werkzeug's `Rule` carries both `subdomain` and `host` attributes, but only one is ever meaningful per Map: when `Map.host_matching=False` (Flask's default), `Rule.bind()` defaults `rule.subdomain` to `map.default_subdomain` (`""`) so it is always populated (never `None`) on any bound rule; `rule.host` stays unused. When `Map.host_matching=True`, the reverse holds: `rule.subdomain` stays `None` and `rule.host` is used instead. werkzeug's `Map.add` raises `RuntimeError` if a subdomain is supplied together with `host_matching=True`, so the two never coexist on one rule. Any code iterating `url_map.iter_rules()` to report per-rule domain info must branch on `app.url_map.host_matching` to pick the right attribute.

## References

### X1 — No built-in full-domain-per-rule resolver in werkzeug or Flask

Checked werkzeug/routing/rules.py, werkzeug/routing/map.py, and Flask's src/flask/app.py for any helper that combines a Rule's subdomain/host with SERVER_NAME into a full domain string, for use outside of a live request/adapter context. None exists. The nearest relative, `MapAdapter`'s netloc construction (werkzeug/routing/map.py, `f"{self.subdomain}.{self.server_name}"`), requires a bound adapter (`Map.bind(server_name, ...)`) and is used for `url_for`/external URL building, not static rule listing. Code that wants a static "domain per rule" view (e.g. `flask routes` CLI output) must construct it manually: `f"{rule.subdomain}.{SERVER_NAME or ''}"` if `rule.subdomain` else `SERVER_NAME or ''` (guarding host_matching separately per [[flask-routing-internals#R1]]).
