| Stage | Check | Bare | Phronix |
|---|---|---|---|
| setup | DFTracer installed from specified GitLab develop | workaround | OK |
|  | installed build is a real versioned release | OK | OK |
|  | isolated per-run environment | workaround | OK |
| annotate | VCF read path annotated | OK | OK |
|  | per-individual write path annotated | OK | OK |
|  | annotations linted | WRONG | OK |
|  | independent validation performed | WRONG | OK |
| smoke | smoke test runs to completion | OK | OK |
| trace | trace produced with application events | OK | OK |
|  | trace covers the I/O hot path | OK | OK |
|  | every instrumented region has a span | WRONG | OK |
| **Total** | **checks correct** | **6/11** | **11/11** |
