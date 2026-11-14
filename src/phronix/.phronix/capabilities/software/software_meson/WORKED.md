# What worked: software_meson

- [flux-fiction/build/meson] pkg-config --exists flux-core succeeds -> meson setup <builddir> -Duse_system_flux=true; meson compile -C <builddir>; meson install -C <builddir>; with add_project_arguments('-D_GNU_SOURCE', language: 'c') for Cray clang. 2026-07-16.
- [tool:session_configure] session_configure / session_build_install / session_build_annotated drive meson natively (since 2026-07-16).
