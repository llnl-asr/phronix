"""The MCP tools phronix ships with — its built-in capabilities.

Twelve services, each registering a related group of tools:

====================  =====================================================
context_service       context_skills / context_memory / context_for_task
skills_service        skill_list / skill_index / skill_search / skill_load /
                      skill_create / skill_write / skill_write_lesson
authoring_service     skill_define / agent_define  (declarative, idempotent)
memory_service        memory_list / memory_recall / memory_read / memory_write
graph_service         graph_ensure / graph_query / graph_get_node
privacy_service       privacy_scan / privacy_redact / privacy_suspects /
                      privacy_add_pattern
research_service      research_assess / research_define_fom /
                      research_add_approach / research_choose /
                      research_write_plan / research_record_achieved /
                      research_verify / research_status
capability_service    capability_list / capability_new
verification_service  verify_list / verify_run / verify_coverage / verify_new
complexity_service    complexity_assess / complexity_reassess /
                      complexity_impact
profiling_service     profile_bind / profile_step_begin /
                      profile_step_end / profile_status / profile_report
sync_service          agents_sync / permissions_sync / hooks_sync /
                      skills_sync / phronix_status
====================  =====================================================

Together they are the machinery of the learn-and-verify loop:

* ``research_*`` runs BEFORE the work when the catalogue does not cover the
  subject: it turns "attempt and hope" into a measured choice of approach plus
  the capabilities that approach needs;
* ``context_*`` is where an agent STARTS — the graph-backed split between "how do
  I do this" (skills) and "what was learned about this" (memory), returning exact
  sections rather than whole documents.
* the write tools are how a session records what it just learned;
* the capability tools turn a deterministic procedure into code;
* the verification tools are the corrector half — they say whether any of it is
  still TRUE, rather than merely written down;
* the sync tools push all of it out to the four harnesses.

``context_service`` is registered first deliberately. Tool order influences what a
model reaches for, and the retrieval tools should be the first thing it sees.

Capabilities authored at runtime are loaded separately by
:func:`phronix.capabilities.load_all`, from the layered store rather than from
this package — an installed wheel is read-only, and learning that could only be
written into it would not be learning at all.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

#: Registration functions, in the order the server calls them.
REGISTRARS: List[str] = [
    "phronix.mcp_tools.tools.context_service:register",
    "phronix.mcp_tools.tools.skills_service:register",
    "phronix.mcp_tools.tools.layout_service:register",
    "phronix.mcp_tools.tools.schema_service:register",
    "phronix.mcp_tools.tools.solution_service:register",
    "phronix.mcp_tools.tools.authoring_service:register",
    "phronix.mcp_tools.tools.memory_service:register",
    "phronix.mcp_tools.tools.graph_service:register",
    "phronix.mcp_tools.tools.privacy_service:register",
    "phronix.mcp_tools.tools.research_service:register",
    "phronix.mcp_tools.tools.capability_service:register",
    "phronix.mcp_tools.tools.verification_service:register",
    "phronix.mcp_tools.tools.complexity_service:register",
    "phronix.mcp_tools.tools.profiling_service:register",
    "phronix.mcp_tools.tools.sync_service:register",
    "phronix.mcp_tools.tools.conversation_service:register",
]


def register_all(mcp: Any) -> Dict[str, Any]:
    """Register every built-in service on *mcp*.

    A service that fails to import is reported and skipped rather than aborting
    the server, for the same reason a broken learned capability is: partial tool
    coverage is recoverable, a server that will not start is not.
    """
    loaded: List[str] = []
    failed: List[Dict[str, str]] = []
    for spec in REGISTRARS:
        module_name, _, attr = spec.partition(":")
        try:
            module = __import__(module_name, fromlist=[attr])
            register: Callable[[Any], None] = getattr(module, attr)
            register(mcp)
            loaded.append(module_name.rsplit(".", 1)[-1])
        except Exception as exc:
            failed.append({"service": module_name, "error": f"{type(exc).__name__}: {exc}"})
    return {"loaded": loaded, "failed": failed}
