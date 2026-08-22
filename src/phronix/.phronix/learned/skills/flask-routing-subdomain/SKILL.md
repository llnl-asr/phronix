---
name: flask-routing-subdomain
description: The flask-routing-subdomain subject.
subject: flask-routing-subdomain
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Bound rule.subdomain is empty string, never None |
| `R2` | Rules | create_url_adapter and url_for's differing behavior on missing SERVER_NAME |
| `R3` | Rules | iter_rules() needs no request/adapter/SERVER_NAME — it's static Map/Rule data |
| `X1` | References | Default SERVER_NAME config value |





## Instructions

## Rules

### R1 — Bound rule.subdomain is empty string, never None

Once a werkzeug Rule is bound to a Map (happens as soon as Flask's app.add_url_rule registers it into self.url_map), rule.subdomain for a rule declared without an explicit subdomain is `''` (empty string), not `None`. Falsy/`or` checks (`rule.subdomain or default`) work to detect "no subdomain"; an `is None` check never matches and is a bug. Confirmed empirically against werkzeug: `Rule('/foo', endpoint='foo')` added to a `Map()` yields `r.subdomain == ''`; `Rule('/bar', subdomain='api')` yields `'api'`.

### R2 — create_url_adapter and url_for's differing behavior on missing SERVER_NAME

src/flask/app.py create_url_adapter (~line 1874-1912): with an active request, it always uses `self.url_map.default_subdomain or None` and binds via `bind_to_environ` — SERVER_NAME is not required since host can be inferred from environ. WITHOUT a request context, it only proceeds if `self.config["SERVER_NAME"] is not None`; otherwise it returns `None` silently (no exception). The RuntimeError ("Unable to build URLs outside an active request without 'SERVER_NAME' configured...") is raised one level up, in `url_for` (~line 1678-1686), only when it gets `None` back from create_url_adapter in the no-app-context branch. So "missing SERVER_NAME" by itself never raises — only url_for's specific handling of a None adapter does.

### R3 — iter_rules() needs no request/adapter/SERVER_NAME — it's static Map/Rule data

current_app.url_map.iter_rules() (what routes_command in src/flask/cli.py uses) reads static Rule/Map metadata (endpoint, methods, rule pattern, subdomain) that is set once at registration time (app.add_url_rule). This does not require an active request, a URL adapter, or SERVER_NAME to be configured — unlike url_for/create_url_adapter, which build an absolute/bound URL and do require those. Code that only lists routes should not need to reproduce url_for's SERVER_NAME-missing crash; it can fall back gracefully (blank, or show SERVER_NAME if set) since no absolute URL is being built.

## References

### X1 — Default SERVER_NAME config value

Flask's default app config sets `"SERVER_NAME": None` (src/flask/app.py:315). Any code formatting a domain string from SERVER_NAME must guard against None to avoid producing literal "None" in output (e.g. "api.None").
