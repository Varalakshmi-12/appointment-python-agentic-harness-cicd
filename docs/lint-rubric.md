# 1. Quality Rubric

## 1.1 Dimensions

### 1.1.1 Lint Execution Accuracy

Measures whether the agent actually ran the linter and reported its real output. A high score requires the reported result to match what the linter actually produced; a low score means the agent guessed, assumed, or fabricated results.

### 1.1.2 Finding Coverage

Measures how completely the summary reflects the linter's actual findings. A high score requires every issue category in the linter output to appear in the summary with nothing invented; a low score means material findings are omitted or made up.

### 1.1.3 Summary Organization

Measures how usefully the findings are grouped, counted, or prioritized rather than dumped as a flat list. A high score requires findings grouped by rule/severity with counts; a low score is an undifferentiated wall of output.

### 1.1.4 Recommendation Quality

Measures whether the agent's recommendation follows logically from the findings. A high score requires a clear, actionable recommendation consistent with the lint result; a low score means the recommendation is missing, vague, or contradicts the findings.

## 1.2 Alternatives Considered

Alternatives considered: a binary pass/fail on "did it lint the code." Ruled out because it cannot distinguish an agent that ran the linter but summarized it poorly from one that both ran it and produced an actionable summary -- and that difference is exactly what I want to improve between runs.

## Scoring Guide

### Lint Execution Accuracy

**1 - Does not meet:** The agent did not run the linter or reported results that don't match its output.
*Example: "The code looks clean" with no linter actually executed.*

**2 - Partially meets:** The linter was run but the reported result is partly inaccurate or ambiguous.
*Example: Reports "a few style issues" without the real counts the linter produced.*

**3 - Meets:** The agent ran the linter and accurately reported its real output.
*Example: "flake8 reported 12 issues" matching the actual run.*

**4 - Exceeds:** Accurately reports results and includes supporting evidence (exact counts per rule, the command used).
*Example: Shows the command, total count, and a per-rule breakdown that matches the output.*

### Finding Coverage

**1 - Does not meet:** Major issue categories in the linter output are omitted or fabricated.
*Example: Output has E501 and F401 issues; summary mentions neither, or invents ones not present.*

**2 - Partially meets:** Captures some categories but omits at least one that appeared.
*Example: Mentions line-length issues but omits unused-import issues that were reported.*

**3 - Meets:** Every issue category in the output appears in the summary; nothing invented.
*Example: All reported rule codes are represented in the summary.*

**4 - Exceeds:** Full coverage plus counts per category and any notable patterns.
*Example: "E501 x8 (long lines), F401 x2 (unused imports), W291 x1" with a note on where they cluster.*

### Summary Organization

**1 - Does not meet:** Raw linter output pasted with no grouping or interpretation.
*Example: The entire flake8 log copied verbatim with no structure.*

**2 - Partially meets:** Some grouping but still hard to scan.
*Example: A long flat list with no counts or priority.*

**3 - Meets:** Findings grouped by rule/type with counts.
*Example: Issues organized under headings by rule code with counts.*

**4 - Exceeds:** Grouped, counted, and prioritized so the most important issues are immediately visible.
*Example: Blocking issues separated from style nits, ordered by importance.*

### Recommendation Quality

**1 - Does not meet:** No recommendation, or one that contradicts the findings.
*Example: "Ready to proceed" when the linter reported errors.*

**2 - Partially meets:** A recommendation is given but is vague or not tied to the findings.
*Example: "Could be cleaner" with no specific next step.*

**3 - Meets:** A clear recommendation consistent with the lint result.
*Example: "12 style issues, none blocking; safe to proceed after cleanup."*

**4 - Exceeds:** Clear recommendation with specific, prioritized next steps drawn from the findings.
*Example: "Fix the 2 unused imports first (quick win), then address long lines; no blocking errors."*

## Pass Threshold

A run is passing if it scores 3 or higher on all dimensions.

Reasoning: For a lint-review workflow to be trustworthy, the agent must actually run the linter, report real findings completely, organize them usefully, and give a sound recommendation. A weakness in any one of these makes the summary misleading or unactionable, so a dimension floor is appropriate.

## Notes on Threshold Design

Considered an aggregate minimum (e.g., 12/16). Ruled out because a run that fabricates findings (1 on Lint Execution Accuracy) could still "pass" on points by being well-organized and confident -- which is the worst failure mode for a review tool. The dimension floor blocks that.
