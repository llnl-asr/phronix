---
name: django-django-13230
description: Adds item_comments() method to Django Feed base class so feed authors can define comments URLs directly without overriding item_extra_kwargs. The method returns None by default and is wired up in get_feed() via _get_dynamic_attr('item_comments', item).
subject: django-syndication-item-comments
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem solved |
| `I2` | Instructions | Add comments support in syndication Feed |
| `I3` | Instructions | What problem it solves |
| `I4` | Instructions | The key idea |
| `I5` | Instructions | Instructions to solve it |
| `I6` | Instructions | Constraints and rules |
| `I7` | Instructions | Pitfalls and lessons |
| `R1` | Rules | Do not break existing feed output |
| `R2` | Rules | Must return None by default |
| `R3` | Rules | Must wire in get_feed() |
| `R4` | Rules | Follow existing pattern |
| `R5` | Rules | No test modifications |
| `R6` | Rules | All 24 tests must pass |

## Instructions

### I1 — Problem solved

The failing test `test_rss2_feed` raised an `IndexError` because the syndication view expected an `item_comments` attribute that was missing. This skill applies when a Django syndication feed test fails due to missing item comment data.

### I2 — Add comments support in syndication Feed

In django/contrib/syndication/views.py, modify the Feed class's item generation to include a `comments` attribute: add `comments=getattr(item, 'comments', None),` before `**self.item_extra_kwargs(item)`.

### I3 — What problem it solves

A later run arriving with a failing test or a feed that needs comments support can recognize this is the right skill by the symptom: they need to add a comments URL/field to feed items but currently have to override item_extra_kwargs() to pass the `comments` parameter to feed.add_item(). This skill solve that problem by providing an item_comments() method on the Feed base class.

### I4 — The key idea

The `item_comments()` method on the Feed base class in django/contrib/syndication/views.py returns None by default and can be overridden by feed authors to return a comments URL. It is used in get_feed() via self._get_dynamic_attr('item_comments', item), making comments directly usable without the item_extra_kwargs workaround.

### I5 — Instructions to solve it

1. In django/contrib/syndication/views.py, add an `item_comments(self, item)` method to the Feed class that returns None (add after item_enclosures, before _get_dynamic_attr).
2. In the same file, in the get_feed() method, add `comments=self._get_dynamic_attr('item_comments', item)` to the feed.add_item() call (after author_link, before categories).
3. The comments parameter already works in feedgenerator.py - this change provides the convenient method on the view side.
4. All 24 syndication tests pass with these changes (1 target test + 23 regression tests).

### I6 — Constraints and rules

1. The item_comments() method must return None by default (cannot have a different default).
2. The _get_dynamic_attr('item_comments', item) call in get_feed() must be added in the exact position shown (after author_link, before categories).
3. Cannot modify any test files.
4. The comments parameter already exists in feedgenerator.py - this only adds the method on the view side.
5. All existing regression tests (23 of them) must continue to pass.
6. The single target test must pass.

### I7 — Pitfalls and lessons

PITFALL: If the _get_dynamic_attr call is placed in the wrong position in get_feed(), it may override other parameters or cause unexpected behavior. The exact position after author_link and before categories is critical.

PITFALL: If item_comments() is added but not wired up in get_feed() via _get_dynamic_attr, the method exists but has no effect - feed authors won't see any difference.

LESSON: The comments parameter was already fully supported in feedgenerator.py (SyndicationFeed.add_item accepts comments=None, and Rss201rev2Feed renders it). The only missing piece was the item_comments() method on the Feed base class to make it conveniently accessible to feed authors without overriding item_extra_kwargs().

LESSON: Following the exact pattern of existing methods (item_title, item_description, item_link, item_enclosures) ensures consistency and that all existing tests continue to pass.

## Rules

### R1 — Do not break existing feed output

All existing RSS2 feed elements and order must remain unchanged; the added `comments` attribute should only appear when the item provides it.

### R2 — Must return None by default

The item_comments(self, item) method must return None as its default value.

### R3 — Must wire in get_feed()

The _get_dynamic_attr('item_comments', item) must be added to the feed.add_item() call in get_feed().

### R4 — Follow existing pattern

The method must follow the same structure as item_title(), item_description, etc. in the Feed class.

### R5 — No test modifications

Cannot modify any test files.

### R6 — All 24 tests must pass

The 1 target test + 23 regression tests must all pass after the change.

## References

- `skill_load(name="django-django-13230", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
