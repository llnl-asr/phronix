# Lessons: phronix_mcp_first

- [L-b480d3ff] pecan_milan on corona: session_configure 'Unsupported build tool: unknown', session_build_install 'Unknown build tool: unknown', session_install_dftracer 'dftracer pip install failed'; the agent fell back to pip and git by hand -> pecan_milan is raw research Python with no setup.py or pyproject.toml, so detection returned build_tool: unknown and every builder refused it -> the fix belongs in the detector (teach it bare-Python workloads), then re-call the tools; a hand-rolled run hides the defect (2026-09-15, dftracer-agents mcp-first E1)
