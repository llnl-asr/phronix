# Lessons: phronix_contribute

- [L-c0ntr1b1] A contribution branch rebased onto a rewritten upstream replayed the old base commit and conflicted in engine files -> a plain `git rebase` replays every commit not in the new base -> replay only the contribution commits (`rebase --onto <new> <recorded base>`) (2026-11-13)
