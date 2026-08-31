def register(mcp):
    @mcp.tool()
    def insert_normpath_call(filepath: str, function_name: str, param_name: str) -> str:
        """Insert 'param = os.path.normpath(param)' at the start of a function.
        
        Args:
            filepath: Path to the Python file
            function_name: Name of the function to modify
            param_name: Name of the parameter to normalize
            
        Returns:
            Status message indicating success or failure
        """
        import re
        
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            # Find the function definition
            func_pattern = re.compile(rf'^def\s+{function_name}\s*\(')
            func_line_idx = None
            
            for idx, line in enumerate(lines):
                if func_pattern.match(line):
                    func_line_idx = idx
                    break
            
            if func_line_idx is None:
                return f"Function '{function_name}' not found in {filepath}"
            
            # Find the first line of the function body (after the signature)
            # Handle multi-line function signatures
            paren_count = 0
            current_idx = func_line_idx
            
            while current_idx < len(lines):
                for char in lines[current_idx]:
                    if char == '(':
                        paren_count += 1
                    elif char == ')':
                        paren_count -= 1
                
                if paren_count == 0 and ')' in lines[current_idx]:
                    # Found the end of the signature, check for colon
                    if ':' in lines[current_idx]:
                        insert_idx = current_idx + 1
                        break
                    else:
                        # Colon might be on the next line
                        current_idx += 1
                        if current_idx < len(lines) and ':' in lines[current_idx]:
                            insert_idx = current_idx + 1
                            break
                
                current_idx += 1
            else:
                return f"Could not find function body for '{function_name}'"
            
            # Determine indentation of the first body line
            if insert_idx < len(lines):
                indent_match = re.match(r'^(\s*)', lines[insert_idx])
                indent = indent_match.group(1) if indent_match else '    '
            else:
                indent = '    '
            
            # Insert the normpath call
            normpath_line = f"{indent}{param_name} = os.path.normpath({param_name})\n"
            lines.insert(insert_idx, normpath_line)
            
            # Write back
            with open(filepath, 'w') as f:
                f.writelines(lines)
            
            return f"Successfully inserted normpath call at line {insert_idx + 1} in {filepath}"
            
        except Exception as e:
            return f"Error inserting normpath call: {str(e)}"
