def register(mcp):
    @mcp.tool()
    def generate_instances() -> str:
        """Return a JSON string of a list of instance dicts for the pylint notes bug.
        Each instance includes name, behaviour, command, expected, source.
        """
        import json
        instances = []
        tag_variants = {
            "punctuation": ["???", "!!!"],
            "alphanumeric": ["YES", "NO"],
            "mixed": ["??YES", "YES??"],
            "empty": [""]
        }
        idx = 1
        # Single tag instances
        for tag_type, variants in tag_variants.items():
            for tag in variants:
                name = f"instance_{tag_type}_single_{idx}"
                tags_str = tag
                command = f"pylint test.py --notes=\"{tags_str}\""
                behaviour = f"Single {tag_type} tag: '{tag}'"
                expected = "W0511 warning for the tag if non-empty"
                instances.append({
                    "name": name,
                    "behaviour": behaviour,
                    "command": command,
                    "expected": expected,
                    "source": "generated"
                })
                idx += 1
        # Multiple tag instances (two tags separated by comma)
        for tag_type, variants in tag_variants.items():
            for tag1 in variants:
                for tag2 in variants:
                    # avoid duplicate empty tags combination
                    if tag1 == "" and tag2 == "":
                        continue
                    name = f"instance_{tag_type}_multiple_{idx}"
                    tags_str = f"{tag1},{tag2}"
                    command = f"pylint test.py --notes=\"{tags_str}\""
                    behaviour = f"Multiple {tag_type} tags: '{tag1}' and '{tag2}'"
                    expected = "W0511 warning for each non-empty tag"
                    instances.append({
                        "name": name,
                        "behaviour": behaviour,
                        "command": command,
                        "expected": expected,
                        "source": "generated"
                    })
                    idx += 1
                    if len(instances) >= 20:
                        break
                if len(instances) >= 20:
                    break
            if len(instances) >= 20:
                break
        # Ensure exactly 20 instances
        return json.dumps(instances[:20])
