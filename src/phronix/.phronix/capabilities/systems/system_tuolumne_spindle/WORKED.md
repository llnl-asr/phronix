# What worked: system_tuolumne_spindle

- [pecan/run/spindle_disable] 2026-07-22, Tuolumne, PECAN 4 nodes x 16 ranks, exclusive allocation: `export SPINDLE_FLUXOPT=disable` in the submitting shell, then `flux run ...`: import-to-first-training-step mean 47.3s over 5 replicates (min 36.4s, max 65.9s), vs 143.5-185.1s for medium/high.
