# Lessons: software_pip

- [L-5be413d3] mesonpy project (flux-fiction) has a use_system_flux meson option that plain `pip install .` cannot set -> pip has no way to pass project-specific meson -D flags except through config-settings -> pip install --no-build-isolation --config-settings=setup-args="-Duse_system_flux=true" . (or flux_prefix similarly). Observed on Tuolumne with flux-core. (2026-07-16)
