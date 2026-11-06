# PRD: Backend Lint Review Workflow

**Stakeholder:** The backend engineer shipping Flask changes, who needs lint findings triaged (cosmetic vs functional) without spending their own review time on style issues.

**Failure modes:** linter not installed at runtime; false "ready to proceed" when a functional bug hides among style warnings; report overwritten or not saved.

## Workflow Description

This workflow runs a Python linter over the Flask backend and produces a prioritized summary of the issues it finds.

## Trigger

A developer invokes `claude "[task prompt]"` from the root of the container's /workspace, asking the agent to lint the backend and summarize the results. For this module the workflow is initiated manually; there is no automated hook.

## Decision Events

- If the linter runs cleanly with no issues, the agent reports that the backend passed with no findings and recommends proceeding.
- If the linter reports issues, the agent summarizes them grouped by type/severity and recommends which to fix first; it does NOT edit any source files to fix them.
- If the linter is not installed, the agent installs it so the check can run, rather than skipping the check.

## Actions

1. Identify the backend source file(s) to lint (appointment-backend/app.py and any other .py files).
2. Run the linter (flake8) over the backend source inside the container.
3. Capture the linter's full output.
4. Group and count the findings by rule/category.
5. Produce a prioritized summary of the most important issues and a recommendation, without modifying any source files.

## Acceptance Criteria

- The agent actually runs the linter and reports its real output (not an invented or assumed result).
- The summary reflects the actual findings: every issue category present in the linter output appears in the summary, and none are invented.
- The findings are grouped or counted rather than listed as an undifferentiated dump.
- The agent provides a clear recommendation consistent with the linter result.
- No source files were modified.
