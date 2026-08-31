---
name: psf-requests-2148
description: Fix uncaught socket.error in requests usage
subject: psf-requests-2148
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Identify failing test due to Docker pull rate limit |
| `I2` | Instructions | Problem |
| `I3` | Instructions | Naming |

## Instructions

### I1 — Identify failing test due to Docker pull rate limit

When a task fails with an isolation error like `You have reached your unauthenticated pull rate limit`, recognize that the Docker image cannot be pulled anonymously.

### I2 — Problem

Raw socket errors from the requests library bubble up as socket.error instead of being wrapped in requests.exceptions.ConnectionError, causing uncaught exceptions in client code.

### I3 — Naming

Use a concise, kebab-case skill name that reflects the problem, e.g., `psf-requests-2148`. This allows later runs to load the skill directly via `skill_load("psf-requests-2148")`.

## References
