#!/bin/bash
# check_errors.sh - Check for known code errors in the project
# Errors checked:
#   1. Tensor not callable: model parameter lacks type annotation in Translator.py
#   2. seq_lens possibly unbound: used outside loop without initialization in Translator.py
#   3. np not accessed: unused numpy import in project files
#   4. tb_writer possibly unbound: conditionally assigned but not initialized in train_modern.py
#   5. Repository-wide static type checks for Python files

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
ERRORS_FOUND=0

echo "=========================================="
echo " Code Error Checker"
echo "=========================================="
echo ""

# --- Error 1: Tensor not callable / Attribute "__call__" is unknown ---
echo "[Check 1] Tensor not callable: missing type annotation for 'model' in Translator.py"
FILE="$PROJECT_DIR/transformer/Translator.py"
if [ -f "$FILE" ]; then
    # Check if __init__ parameter 'model' lacks a Transformer type annotation
    if grep -Pq 'def __init__\(' "$FILE" && ! grep -Pq 'model:\s*Transformer' "$FILE"; then
        echo "  ERROR: In $FILE, the 'model' parameter in __init__ has no type annotation."
        echo "         Static type checkers cannot infer that model.trg_word_prj is nn.Linear (callable)."
        echo "  FIX:   Add type annotation 'model: Transformer' and import Transformer."
        ERRORS_FOUND=$((ERRORS_FOUND + 1))
    else
        echo "  OK: 'model' parameter has Transformer type annotation."
    fi
else
    echo "  SKIP: $FILE not found."
fi
echo ""

# --- Error 2: seq_lens possibly unbound ---
echo "[Check 2] 'seq_lens' is possibly unbound in Translator.py"
if [ -f "$FILE" ]; then
    # Check if seq_lens is initialized before the for loop
    # Look for seq_lens assignment OUTSIDE the for loop (before it)
    # If seq_lens only appears inside the for loop body, it's possibly unbound
    IN_LOOP_ONLY=true
    if grep -Pq '^\s+seq_lens\s*=' "$FILE"; then
        # Check if there's a seq_lens initialization BEFORE the for-loop line
        LOOP_LINE=$(grep -n 'for step in range' "$FILE" | head -1 | cut -d: -f1)
        INIT_LINE=$(grep -n 'seq_lens\s*=' "$FILE" | head -1 | cut -d: -f1)
        if [ -n "$LOOP_LINE" ] && [ -n "$INIT_LINE" ]; then
            if [ "$INIT_LINE" -lt "$LOOP_LINE" ]; then
                IN_LOOP_ONLY=false
            fi
        fi
    fi
    if $IN_LOOP_ONLY; then
        echo "  ERROR: In $FILE, 'seq_lens' is only assigned inside the for loop."
        echo "         If the loop never executes, seq_lens will be unbound at the return statement."
        echo "  FIX:   Initialize 'seq_lens = torch.zeros(...)' or similar before the for loop."
        ERRORS_FOUND=$((ERRORS_FOUND + 1))
    else
        echo "  OK: 'seq_lens' is initialized before the for loop."
    fi
else
    echo "  SKIP: $FILE not found."
fi
echo ""

# --- Error 3: 'np' is not accessed (unused numpy import) ---
echo "[Check 3] 'np' is not accessed: unused numpy imports"
# Only check project .py files, exclude .venv and __pycache__
while IFS= read -r pyfile; do
    if grep -Pq '^import numpy as np' "$pyfile"; then
        # Count usages of 'np.' excluding the import line itself
        NP_USAGES=$(grep -c 'np\.' "$pyfile" 2>/dev/null || true)
        if [ "$NP_USAGES" -eq 0 ]; then
            echo "  ERROR: In $pyfile, 'import numpy as np' exists but 'np' is never used."
            echo "  FIX:   Remove the unused 'import numpy as np' line."
            ERRORS_FOUND=$((ERRORS_FOUND + 1))
        fi
    fi
done < <(find "$PROJECT_DIR" -name '*.py' -not -path '*/.venv/*' -not -path '*/__pycache__/*')
echo ""

# --- Error 4: 'tb_writer' is possibly unbound ---
echo "[Check 4] 'tb_writer' is possibly unbound in train_modern.py"
TRAIN_FILE="$PROJECT_DIR/train_modern.py"
if [ -f "$TRAIN_FILE" ]; then
    # tb_writer is problematic if it's assigned only inside an if-block
    # but never initialized with a default value (e.g. tb_writer = None) before that block.
    # Check: does tb_writer get a default assignment BEFORE the first conditional assignment?
    FIRST_ASSIGN=$(grep -n 'tb_writer\s*=' "$TRAIN_FILE" | head -1 | cut -d: -f1)
    CONDITIONAL_ASSIGN=$(grep -n 'if.*use_tb' "$TRAIN_FILE" | head -1 | cut -d: -f1)
    if [ -n "$FIRST_ASSIGN" ] && [ -n "$CONDITIONAL_ASSIGN" ]; then
        if [ "$FIRST_ASSIGN" -gt "$CONDITIONAL_ASSIGN" ]; then
            echo "  ERROR: In $TRAIN_FILE, 'tb_writer' is only assigned inside 'if opt.use_tb:' (line $CONDITIONAL_ASSIGN)."
            echo "         Static type checkers flag it as possibly unbound when used later."
            echo "  FIX:   Initialize 'tb_writer = None' before the conditional block."
            ERRORS_FOUND=$((ERRORS_FOUND + 1))
        else
            echo "  OK: 'tb_writer' is initialized before the conditional block."
        fi
    elif [ -z "$FIRST_ASSIGN" ]; then
        echo "  SKIP: 'tb_writer' not found in $TRAIN_FILE."
    else
        echo "  OK: No conditional assignment pattern detected."
    fi
else
    echo "  SKIP: $TRAIN_FILE not found."
fi
echo ""

# --- Error 5: repository-wide static type check ---
echo "[Check 5] Repository-wide static type checks"
PYRIGHT_CMD=()
PYTHON_PATH=""

if command -v pyright >/dev/null 2>&1; then
    PYRIGHT_CMD=(pyright)
elif command -v npx >/dev/null 2>&1; then
    PYRIGHT_CMD=(npx -y pyright)
fi

if [ -x "$PROJECT_DIR/.venv/bin/python" ]; then
    PYTHON_PATH="$PROJECT_DIR/.venv/bin/python"
elif [ -x "$PROJECT_DIR/venv/bin/python" ]; then
    PYTHON_PATH="$PROJECT_DIR/venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_PATH="$(command -v python3)"
fi

if [ "${#PYRIGHT_CMD[@]}" -eq 0 ]; then
    echo "  SKIP: pyright not available and npx not found."
else
    PYRIGHT_ARGS=()
    if [ -n "$PYTHON_PATH" ]; then
        PYRIGHT_ARGS+=(--pythonpath "$PYTHON_PATH")
    fi

    mapfile -t PY_FILES < <(find "$PROJECT_DIR" -name '*.py' \
        -not -path '*/.venv/*' \
        -not -path '*/venv/*' \
        -not -path '*/__pycache__/*' \
        -not -path '*/old_files/*' | sort)

    if [ "${#PY_FILES[@]}" -eq 0 ]; then
        echo "  SKIP: no Python files found for type checking."
    else
        set +e
        PYRIGHT_OUTPUT=$("${PYRIGHT_CMD[@]}" "${PYRIGHT_ARGS[@]}" "${PY_FILES[@]}" 2>&1)
        PYRIGHT_EXIT=$?
        set -e

        if [ "$PYRIGHT_EXIT" -ne 0 ]; then
            echo "  ERROR: Static type checker found repository issues."
            echo "$PYRIGHT_OUTPUT" | sed 's/^/         /'
            ERRORS_FOUND=$((ERRORS_FOUND + 1))
        else
            echo "  OK: Static type checker reported no repository issues."
        fi
    fi
fi
echo ""

# --- Summary ---
echo "=========================================="
if [ "$ERRORS_FOUND" -gt 0 ]; then
    echo " RESULT: $ERRORS_FOUND error(s) found. Please fix them."
    exit 1
else
    echo " RESULT: All checks passed. No errors found."
    exit 0
fi
