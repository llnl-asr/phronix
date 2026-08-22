SPEC = {
    "kind": "capability",
    "target": "run_pytest",
    "claim": "Running pytest returns a dict with keys 'stdout', 'stderr', and 'returncode' where 'returncode' is an integer.",
    "inputs": [],
    "outputs": [{"name": "result", "check": "lambda ctx: isinstance(ctx['result'], dict) and 'returncode' in ctx['result'] and isinstance(ctx['result']['returncode'], int)"}],
    "assumptions": [],
    "constraints": [],
    "invariants": []
}

def register(mcp):
    @mcp.verifier()
    def verify_run_pytest():
        result = mcp.invoke_tool('run_pytest')
        return {"result": result}
