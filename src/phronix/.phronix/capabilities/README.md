# Bundled capabilities

MCP tools the framework built for itself and that were general enough to promote
into the shipped package (`phronix contribute`).

Each file is one module exposing `register(mcp)`; the MCP server discovers and
loads them on start. See the `phronix-capability-authoring` skill for the
contract, the docstring conventions, and how to choose a layer.

This directory ships empty on purpose. A capability belongs here only if it
assumes nothing about any particular repository — most useful ones assume
something, and correctly live in a project's own `.phronix/capabilities/`.
