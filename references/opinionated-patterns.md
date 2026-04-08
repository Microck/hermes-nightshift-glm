# Opinionated Best-Practice Patterns

Language-agnostic best practices for non-React projects. Pick ONE pattern per task run.

## Python

### 1. No Bare `except:`

**Anti-pattern:**
```python
try:
    do_something()
except:
    pass
```

**Fix:** Catch specific exceptions:
```python
try:
    do_something()
except ValueError as e:
    raise ValueError(f"Failed to do something: {e}") from e
```

---

### 2. No Mutable Default Arguments

**Anti-pattern:**
```python
def add_item(item, items=[]):
    items.append(item)
    return items
```

**Fix:** Use `None`:
```python
def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
```

---

### 3. No `print()` for Debugging

**Anti-pattern:**
```python
print("debug:", value)
```

**Fix:** Use `logging`:
```python
import logging
logger = logging.getLogger(__name__)
logger.debug("value: %s", value)
```

---

### 4. Type Hints Missing

**Anti-pattern:**
```python
def process(data):
    return data.get("key")
```

**Fix:** Add type hints:
```python
from typing import Any
def process(data: dict[str, Any]) -> Any:
    return data.get("key")
```

---

### 5. Resource Leaks — Unclosed Files/Connections

**Anti-pattern:**
```python
f = open("file.txt")
content = f.read()
# f never closed
```

**Fix:** Use context manager:
```python
with open("file.txt") as f:
    content = f.read()
```

---

## Go

### 1. Error Wrapping Missing

**Anti-pattern:**
```go
if err != nil {
    return err
}
```

**Fix:** Wrap with context:
```go
if err != nil {
    return fmt.Errorf("processFile: %w", err)
}
```

---

### 2. No Context Propagation

**Anti-pattern:**
```go
func FetchData(url string) ([]byte, error) {
    resp, err := http.Get(url)
```

**Fix:** Accept and pass context:
```go
func FetchData(ctx context.Context, url string) ([]byte, error) {
    req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
```

---

### 3. Magic Strings / Numbers

**Anti-pattern:**
```go
if status == "active" {
    retry(5)
}
```

**Fix:** Use constants:
```go
const StatusActive = "active"
const MaxRetries = 5
```

---

## Rust

### 1. `unwrap()` in Production Code

**Anti-pattern:**
```rust
let value = parse(input).unwrap();
```

**Fix:** Use `?` or explicit handling:
```rust
let value = parse(input).map_err(|e| MyError::Parse(e))?;
```

---

### 2. Clone When Borrowing Would Suffice

**Anti-pattern:**
```rust
fn process(data: String) { ... }
let owned = get_data();
process(owned.clone()); // unnecessary clone
```

**Fix:** Borrow instead:
```rust
fn process(data: &str) { ... }
process(&owned);
```

---

## SQL

### 1. String Concatenation in Queries (SQL Injection Risk)

**Anti-pattern:**
```python
query = f"SELECT * FROM users WHERE id = {user_id}"
```

**Fix:** Use parameterized queries:
```python
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

---

### 2. SELECT * in Application Code

**Anti-pattern:**
```sql
SELECT * FROM orders
```

**Fix:** Select only needed columns:
```sql
SELECT id, status, total FROM orders
```

---

## Detection Patterns (What to Search For)

| Pattern | Language | Search |
|---------|----------|--------|
| Bare except | Python | `except:` (no exception type) |
| Mutable default | Python | `def .*=\[\]` or `def .*={}` |
| Debug print | Python | `print(` not in `logging` or `pprint` |
| Unclosed file | Python | `open(` not followed by `with` |
| unwrap() | Rust | `\.unwrap()` in non-test code |
| String concat SQL | Python/JS | `f"SELECT` or template strings in queries |
| No context | Go | `http.Get(` without `WithContext` |
| Magic numbers | Any | Hardcoded numbers > 1 not named |
| TODO in code | Any | `TODO` or `FIXME` comments left in |
