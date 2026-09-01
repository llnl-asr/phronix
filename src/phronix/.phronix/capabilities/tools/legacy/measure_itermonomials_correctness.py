def register(mcp):
    @mcp.tool()
    def measure_itermonomials_correctness():
        """Measure itermonomials correctness rate across the research corpus.
        Returns a float between 0 and 1.
        """
        # Import necessary modules from phronix
        from phronix.research import get_instances, get_topic
        import json, subprocess, sys
        import sympy as sp
        # Retrieve instances for the current topic
        topic = "sympy__sympy-21847"
        instances = get_instances(topic)
        if not instances:
            return 0.0
        passed = 0
        total = 0
        for inst in instances:
            # Each instance should have a command and expected output defined.
            cmd = inst.get("command")
            expected = inst.get("expected")
            if not cmd or expected is None:
                continue
            # Execute the command in a subprocess, capture stdout.
            result = subprocess.run(["bash", "-lc", cmd], capture_output=True, text=True)
            output = result.stdout.strip()
            # Normalize expected and output for comparison.
            # Expected is stored as a string representation of a Python list.
            try:
                expected_obj = eval(expected, {"__builtins__": {}}, {})
            except Exception:
                expected_obj = expected
            # Compare as strings after stripping whitespace.
            if output == str(expected_obj):
                passed += 1
            total += 1
        if total == 0:
            return 0.0
        return passed / total
