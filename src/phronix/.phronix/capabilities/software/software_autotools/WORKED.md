# What worked: software_autotools

- [tool:session_build_annotated] session_build_annotated(run_id) finds dftracer through PKG_CONFIG_PATH=<prefix>/lib/pkgconfig, CPPFLAGS=-I<prefix>/include, LDFLAGS=-L<prefix>/lib -Wl,-rpath,<prefix>/lib (no --with-dftracer flag needed), provided the project's configure.ac probes them.
