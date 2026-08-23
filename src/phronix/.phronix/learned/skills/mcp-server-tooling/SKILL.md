---
name: mcp-server-tooling
description: Operational quirks and failure modes of the mcp-server stage's tooling (graph_query, graph_get_node, the knowledge-graph rebuild).
subject: mcp-server-tooling
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Retry once on knowledge-graph rebuild OSError, then stop calling graph tools for the stage |

## Instructions

## Rules

### R1 — Retry once on knowledge-graph rebuild OSError, then stop calling graph tools for the stage

graph_query/graph_get_node can throw OSError during a knowledge-graph rebuild. Retry once; if the same error recurs, stop calling graph_query/graph_get_node for the rest of the stage rather than retrying repeatedly — see phronix-self-healing R5/X3 and phronix-context-economy R6/X3 for the general retry-once-then-fallback pattern this follows.
