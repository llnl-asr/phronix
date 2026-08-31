def register(mcp):
    @mcp.tool()
    def _patched_convert_dx(dx, x0, xconv, convert):
        """Patched version of Axes._convert_dx.

        Handles the case where ``x0`` (original coordinate array) consists solely of ``np.nan``.
        In such cases the original implementation calls ``cbook._safe_first_finite`` which raises ``StopIteration``.
        The fix returns ``convert(dx)`` directly when all values are NaN, preserving the original behaviour for valid inputs.
        """
        import numpy as np
        # xconv is already a unitless ndarray; if empty, defer to original conversion.
        if xconv.size == 0:
            return convert(dx)
        # If all original x values are NaN, skip the finite check and return converted dx.
        if np.all(np.isnan(x0)):
            return convert(dx)
        # Fallback to original logic.
        try:
            return x0 + dx
        except Exception:
            # Preserve original error handling by delegating to the original method.
            return convert(dx)

    # Monkey‑patch the method in matplotlib.axes._axes.Axes.
    import importlib
    module = importlib.import_module('matplotlib.axes._axes')
    Axes = getattr(module, 'Axes')
    Axes._convert_dx = staticmethod(_patched_convert_dx)
