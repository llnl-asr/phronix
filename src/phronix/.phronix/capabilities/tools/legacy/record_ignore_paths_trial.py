def register(mcp):
    @mcp.tool()
    def record_ignore_paths_trial(instance_name: str, dims_json: str, passed: bool, split: str) -> str:
        """Describe (do not itself call MCP research tools) the trial to record:
        returns a ready-to-use instruction string for
        research_add_instances(topic, instances=[{name, dims}]) followed by
        research_record_trial(topic, name=instance_name, split=split, passed=passed).
        Kept as a formatting/normalization helper since the research_* tools
        themselves are the actual recorders and already deterministic."""
        return (
            f"add_instances: [{{'name': '{instance_name}', 'dims': {dims_json}}}]\n"
            f"record_trial: name={instance_name}, split={split}, passed={passed}"
        )
