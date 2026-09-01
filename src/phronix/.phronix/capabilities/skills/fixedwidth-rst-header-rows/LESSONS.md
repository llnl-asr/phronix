# Lessons — fixedwidth-rst-header-rows

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Header rows not supported: FixedWidth

**2026-08-31** — Header rows not supported: FixedWidth.__init__ lacks header_rows argument; RST.__init__ was changed to accept it but call site not updated, causing TypeError. Also unrelated attribute error in test runner prevented test execution.
Details: In the attempt to allow header_rows in ascii.rst output, FixedWidth class unchanged still expects no header_rows; RST.__init__ was altered to accept header_rows, but its super() call still passes none, leading to unexpected keyword error. This broke the test `test_rst_with_header_rows` and hidden runner error about builtins._xdg_config_home_orig also caused failure. The patch adding header_rows parameter to FixedWidth and modifying RST.__init__ is insufficient; need to also update RST.write or FixedWidth to handle header_rows correctly and fix the test runner environment. No successful behavior observed; therefore record as a lesson.
