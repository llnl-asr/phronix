# Lessons — django-django-15996

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Combined enum flag serialization fix: When EnumSerializer

**2026-08-29** — Combined enum flag serialization fix: When EnumSerializer.serialize() encounters a combined flag value (where .name returns 'A|B' etc., not a valid member), it must decompose the value by iterating through all enum members and checking member.value & self.value.value == member.value to find which members' bits are set. If only one effective member, use single member syntax; if multiple, generate OR expression joining them with ' | '. The try/except pattern checking enum_class[member_name].value == self.value.value handles the single-member case first; if that fails, the decomposition loop handles combined flags.
