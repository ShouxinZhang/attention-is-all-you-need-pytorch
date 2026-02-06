# Development Log - 2026-02-06 07:05:55

## Description
User requested that unused-import detection should cover all `import xxx` statements (not just a few hard-coded modules).

## Root Cause (Why it wasn't detected)
- The previous Check 3 in `check_errors.sh` only matched a small allowlist (`np`, `pickle`, `json`, `os`) using grep.
- Pylance/pyright can report unused imports as warnings, and the script did not fail on warnings.

## Actions Taken
- Upgraded `check_errors.sh` Check 3 to a **general AST-based scanner** that detects unused imports for:
  - `import xxx` (including dotted imports)
  - `from xxx import yyy` (including aliases)
- Implemented basic false-positive controls:
  - Excludes `.venv/`, `venv/`, `old_files/`, `__pycache__/`
  - Treats `__all__` list/tuple string literals as a usage signal (exports)
  - Exempts imports inside `if TYPE_CHECKING:` blocks
- Fixed a real unused import found by the new gate:
  - Removed unused `import torch` from `transformer/Layers.py`

## Files Modified
- [check_errors.sh](check_errors.sh): Replaced old grep-based unused import checks with AST scan.
- [transformer/Layers.py](transformer/Layers.py): Removed unused `import torch`.

## Verification
- `bash check_errors.sh`: PASS
