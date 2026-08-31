---
name: matplotlib-matplotlib-23476
description: Fix DPI doubling on unpickle for Matplotlib figures on M1 Macs
subject: matplotlib-matplotlib-23476
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add DPI guard in Figure.__setstate__ |
| `R1` | Rules | Do not drop existing canvas/manager during unpickle |

## Instructions

### I1 — Add DPI guard in Figure.__setstate__

Insert after restoring __dict__:

```python
if 'dpi' not in self.__dict__:
    self.dpi = mpl.rcParams.get('figure.dpi', 100.0)
```

## Rules

### R1 — Do not drop existing canvas/manager during unpickle

The Figure must retain a functional canvas and manager after deserialization, otherwise size calculations will raise AttributeError.
