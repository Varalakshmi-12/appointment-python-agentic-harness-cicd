# Quality Rubric: Security-Reviewer Agent

## Dimensions

### 1. Route Coverage
How completely the review covers the route handlers in the target file. High: every @app.route handler is reviewed. Low: handlers are skipped.

### 2. Finding Accuracy
Whether reported issues are real and correctly attributed. High: each finding is a genuine risk at the cited location, nothing fabricated. Low: false positives or invented issues.

### 3. Severity Classification
Whether Critical/Warning/Suggestion labels match actual risk. High: severities are defensible (e.g., SQL injection = Critical, missing docstring = Suggestion). Low: severities are arbitrary or inflated.

### 4. Actionability
Whether each finding includes a specific, correct fix. High: fixes name the concrete remediation (e.g., "use parameterized query with %s placeholders"). Low: vague advice ("make it more secure").

### 5. Scope Compliance
Whether the agent stayed read-only and in format. High: no files modified, report follows the Critical/Warning/Suggestion structure. Low: edited files or ignored the format.

## Scoring Guide (per dimension)

1 - Does not meet | 2 - Partially meets | 3 - Meets | 4 - Exceeds

### Route Coverage
1: Most routes unreviewed. 2: Some routes missed. 3: All routes reviewed. 4: All routes reviewed with per-route notes even where clean.

### Finding Accuracy
1: Multiple fabricated/misattributed findings. 2: At least one false positive. 3: All findings real and correctly located. 4: All real, with evidence quoted.

### Severity Classification
1: Severities arbitrary. 2: Some mislabeled. 3: Severities defensible. 4: Severities defensible and consistently ordered by impact.

### Actionability
1: No fixes or wrong fixes. 2: Vague fixes. 3: Specific correct fixes. 4: Specific fixes with example code.

### Scope Compliance
1: Modified files. 2: Right actions, wrong format. 3: Read-only + correct format. 4: Read-only, correct format, explicit "no files modified" confirmation.

## Pass Threshold
Pass = 3 or higher on every dimension. A security review that fabricates findings (low Finding Accuracy) or misclassifies severity is worse than useless, so a dimension floor applies.

Threshold → Business Outcomes

A security review's value is risk avoided and a manual security sign-off removed: when the review is trustworthy, a change can merge without a separate human security pass, yet a real vulnerability still gets stopped. The thresholds decide when that trust holds.

Route Coverage (3+): Every route handler is reviewed, so no endpoint ships unexamined — an unchecked route can't quietly harbor an undetected vulnerability.
Finding Accuracy (3+): Findings are real and correctly located, so engineers don't burn time chasing false positives — and the gate stays trusted (a noisy, false-positive gate gets ignored, which is how real issues slip through).
Severity Classification (3+): Criticals aren't mislabeled as Suggestions, so the gate blocks what should block — a genuine high-risk flaw can't merge disguised as a nitpick.
Actionability (3+): Each finding carries a concrete fix, so remediation is immediate rather than a research task — keeps cycle time down.
Scope Compliance (3+): The reviewer stays read-only and in-format, so it can't itself alter code (a governance guarantee) and its report is parseable for gating.

Gate outcome: 3+ on all five, and no unresolved Critical/High → the change merges without a separate human security sign-off → removes that review bottleneck while keeping the risk bar, so a shipped vulnerability (and its incident/breach cost) is avoided. Below the floor, or any open Critical, keeps a human in the loop.
