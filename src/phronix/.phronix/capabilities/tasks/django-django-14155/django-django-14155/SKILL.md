---
name: django-django-14155
description: The test-tracker subject.
subject: django-django-14155
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem: AxesGrid GeoAxes TypeError |


## Instructions

### I1 — Problem: AxesGrid GeoAxes TypeError

Creating AxesGrid with cartopy GeoAxes as axis_class raises TypeError: 'method' object is not subscriptable. The _tick_only function in axes_grid.py assumes ax.axis supports dict-style access with string keys, but this only works for custom Axes with AxisDict, not GeoAxes where axis is a method.

## Rules

## References
