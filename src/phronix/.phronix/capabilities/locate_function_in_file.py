def register(mcp):
    import subprocess
    
    @mcp.tool()
    def locate_function_in_file(filepath: str, function_name: str) -> str:
        """Locate a function definition in a Python file.
        
        Args:
            filepath: Path to the Python file
            function_name: Name of the function to locate
            
        Returns:
            Line number and context of the function definition
        """
        try:
            result = subprocess.run(
                ["grep", "-n", f"^def {function_name}", filepath],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0 and result.stdout:
                return f"Found function at:\n{result.stdout.strip()}"
            else:
                return f"Function '{function_name}' not found in {filepath}"
                
        except Exception as e:
            return f"Error locating function: {str(e)}"
