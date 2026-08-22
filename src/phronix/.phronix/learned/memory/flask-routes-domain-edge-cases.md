---
name: flask-routes-domain-edge-cases
description: Edge cases for displaying domain/subdomain in Flask routes CLI output
metadata:
  type: reference
---

## Flask Routes Domain Display Edge Cases

When displaying domain/subdomain information in Flask routes CLI output, handle these edge cases:

**1. None values (no domain set)**
```python
domain = rule.host if host_matching else rule.subdomain
row.append(domain or "")  # Convert None → empty string
```
**Why:** Displaying "None" is ugly. Empty string is cleaner and still shows the column exists.

**2. Empty string subdomain (root subdomain)**
```python
# rule.subdomain can be "" (explicitly set to root)
# Display as-is (empty string in output)
# Do NOT convert "" to "-" or "default"
```
**Why:** Empty string subdomain is semantically different from None (explicit root vs no subdomain).

**3. Width calculation with empty strings**
```python
widths = [
    max(len(headers[i]), max(len(str(row[i])) for row in rows))
    for i in range(len(headers))
]
```
**Why:** `len("")` = 0 works fine. Width falls back to header length. The `str()` call handles any type safely.

**4. Sorting empty/None domains**
```python
rules = sorted(rules, key=lambda r: (r.subdomain) or "")
```
**Why:** Empty string sorts before any non-empty string. None must convert to "" for sorting. This puts "no domain" routes at the top when sorting by domain.

**5. All routes have no domain (has_domain = False)**
- Domain column should NOT appear in headers
- Output should be identical to current 3-column format
**Why:** Backward compatibility. Don't show empty columns.

**6. Mixed: some routes have domain, some don't**
- Domain column DOES appear (has_domain = True)
- Routes without domain show empty string in domain column
**Why:** Column presence determined by ANY route having domain, not ALL routes.

**7. host_matching=True vs False**
```python
host_matching = current_app.url_map.host_matching
domain = rule.host if host_matching else rule.subdomain
header = "Host" if host_matching else "Subdomain"
```
**Why:** Flask/Werkzeug uses different attributes based on mode. Display should reflect which mode is active.

**Testing checklist:**
- [ ] None → empty string (not "None")
- [ ] Empty string preserved (not "default")
- [ ] Width calculation doesn't break with empty strings
- [ ] Sorting handles None/empty gracefully
- [ ] has_domain=False produces 3-column output
- [ ] Mixed routes show column with some empty cells
- [ ] Host vs Subdomain header matches mode

**How to apply:** When displaying optional attributes, always handle None, empty string, and mixed presence carefully.
