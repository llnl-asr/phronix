# Lessons: tools_pydftracer

- [L-6172efeb] from dftracer.python import dftracer, dft_fn fails after a successful develop install of dftracer/pydftracer -> typing_extensions is an undeclared runtime dependency. -> pip install typing_extensions; verify with the import check. (2026-07-16)
- [L-3d4519bd] Annotated code imports dftracer.logger / uses @dftracer_fn(comp=...) and fails -> Stale API from an older manual/AST-fallback annotation pass; dftracer.logger does not exist on develop. -> Re-annotate from pristine source with the MCP tool (dftracer.python); never add a shim. (2026-07-16)
- [L-10610156] ModuleNotFoundError: No module named 'dftracer.python' while import dftracer works -> C-core package present without pydftracer. -> Verify with the dftracer.python import before the smoke test; reinstall cleanly into the session venv. (undated)
