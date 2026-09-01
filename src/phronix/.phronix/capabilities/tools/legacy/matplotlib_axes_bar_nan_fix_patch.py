def register(mcp):
    @mcp.tool()
    def apply_matplotlib_axes_bar_nan_fix_patch():
        """Edit lib/matplotlib/axes/_axes.py to make _convert_dx robust to NaN inputs.
        """
        import pathlib, re, textwrap, sys
        path = pathlib.Path('lib/matplotlib/axes/_axes.py')
        text = path.read_text(encoding='utf-8')
        # Find the _convert_dx definition
        start_pat = re.compile(r'def _convert_dx\(dx, x0, xconv, convert\):')
        m = start_pat.search(text)
        if not m:
            return 'Pattern not found'
        # Insert guard after the assert line (which is a few lines after start)
        insert_point = text.find('# x should be an array', m.end())
        if insert_point == -1:
            return 'Insert location not found'
        guard_code = textwrap.dedent('''
            # Guard: if all original x values are NaN, skip the finite check
            if hasattr(x0, 'dtype') and np.all(np.isnan(x0)):
                return convert(dx)
        ''')
        new_text = text[:insert_point] + guard_code + text[insert_point:]
        path.write_text(new_text, encoding='utf-8')
        return 'Patched _convert_dx with NaN guard'
