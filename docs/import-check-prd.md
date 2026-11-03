# PRD: Backend Import/Compile Check Workflow

## Workflow Description

This workflow verifies that every Python file in the Flask backend compiles and imports without errors, and reports the result.

## Trigger

A developer invokes `claude "[task prompt]"` from the root of the container's /workspace, asking the agent to check that the backend Python files compile/import cleanly. For this module the workflow is initiated manually; there is no automated hook.

## Decision Events

- If every backend Python file compiles and imports cleanly, the agent reports success and recommends proceeding.
- If a file fails to compile or import, the agent reports which file failed and the specific error, and recommends against proceeding; it does NOT attempt to fix the code.
- If a dependency needed to import a module is missing, the agent reports the missing dependency rather than silently skipping the file.

## Actions

1. Identify all Python source files in appointment-backend (excluding venv).
2. Run a byte-compile check (python -m py_compile) on each file.
3. Attempt to import the main application module to catch import-time errors.
4. Capture the results (which files passed, which failed, and any error text).
5. Produce a summary and an explicit recommendation on whether the backend is in a runnable state, without modifying any files.

## Acceptance Criteria

- The agent actually runs the compile/import check and reports real results (not assumed).
- Every backend Python file (excluding venv) is accounted for in the report as pass or fail.
- Any failure is reported with the specific file and error message.
- The agent gives an explicit recommendation consistent with the results.
- No source files were modified.