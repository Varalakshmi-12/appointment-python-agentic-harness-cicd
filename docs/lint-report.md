# Lint Report — Backend (flake8)

**Date:** 2026-08-18
**Tool:** flake8 7.3.0 (pycodestyle 2.14.0, pyflakes 3.4.0, mccabe 0.7.0)
**Scope:** `appointment-backend/` (no `venv`/`.venv` directory present in this project, so no exclusion was needed in practice; `--exclude=venv,.venv,env,.env` was passed defensively)
**Command:** `python3 -m flake8 --exclude=venv,.venv,env,.env .` (run from `appointment-backend/`)

Files scanned: `app.py`, `test_mysql.py`, `test_sms.py`

## Summary

| Rule  | Count | Description |
|-------|------:|-------------|
| E501  | 11    | Line too long (> 79 characters) |
| E302  | 11    | Expected 2 blank lines, found 1 (before function/class def) |
| W292  | 2     | No newline at end of file |
| E305  | 1     | Expected 2 blank lines after class/function definition, found 1 |
| **Total** | **25** | |

Findings by file:
- `app.py`: 24 findings (11 × E501, 11 × E302, 1 × E305, 1 × W292)
- `test_mysql.py`: 1 finding (1 × W292)
- `test_sms.py`: 0 findings — clean

## Details

### E302 — expected 2 blank lines, found 1 (11 occurrences, all in `app.py`)
Lines: 12, 54, 75, 108, 118, 128, 140, 233, 261, 293, 373

### E501 — line too long (11 occurrences, all in `app.py`)
| Line | Length |
|------|-------:|
| 173  | 84 |
| 189  | 114 |
| 209  | 106 |
| 212  | 83 |
| 217  | 139 |
| 225  | 85 |
| 247  | 82 |
| 325  | 106 |
| 346  | 139 |
| 362  | 109 |
| 393  | 99 |

### E305 — expected 2 blank lines after class or function definition (1 occurrence)
- `app.py:422`

### W292 — no newline at end of file (2 occurrences)
- `app.py:423`
- `test_mysql.py:13`

## Assessment

All 25 findings are style/formatting issues (blank-line conventions, line length, missing trailing newline). **None are correctness, security, or logic errors** — pyflakes reported zero issues (no unused imports, undefined names, or unused variables), and mccabe reported no complexity warnings.

## Recommendation

**Ready to proceed.** The findings are purely cosmetic PEP 8 violations with no functional risk. They can be fixed trivially (e.g., `black`/`autopep8` or a quick manual pass) at any point without blocking further development. If the team wants a clean baseline before merging, a quick auto-format pass is a low-effort win, but there is no correctness or security reason to hold up work on this codebase.
