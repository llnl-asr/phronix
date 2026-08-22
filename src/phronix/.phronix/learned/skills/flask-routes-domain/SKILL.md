---
name: flask-routes-domain
description: The flask-routes-domain subject.
subject: flask-routes-domain
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Compute domain column using subdomain and SERVER_NAME when host_matching is disabled |


## Instructions

## Rules

### R1 — Compute domain column using subdomain and SERVER_NAME when host_matching is disabled

When host_matching is False, return "subdomain.SERVER_NAME" if both are set, else return whichever is non-empty; if both empty return empty string. This mirrors Flask CLI behavior and ensures correct domain display.

## References
