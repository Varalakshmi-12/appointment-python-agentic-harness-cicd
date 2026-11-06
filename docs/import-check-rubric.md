# 1. Quality Rubric

## 1.1 Dimensions

### 1.1.1 Check Execution Accuracy

Measures whether the agent actually ran the compile/import check and reported real results. A high score requires the reported outcome to match what the commands actually produced; a low score means the agent assumed or fabricated a result.

### 1.1.2 File Coverage

Measures whether every backend Python file (excluding venv) is accounted for in the report. A high score requires each source file to appear as pass or fail; a low score means files were silently skipped.

### 1.1.3 Error Reporting Clarity

Measures how clearly any failures are reported. A high score requires each failure to name the specific file and include the actual error message; a low score means failures are vague or unlocated. (If there are no failures, a clean, explicit "all passed" statement earns full marks.)

### 1.1.4 Recommendation Quality

Measures whether the recommendation follows logically from the results. A high score requires a clear, explicit proceed/don't-proceed recommendation consistent with the check output; a low score means it is missing, vague, or contradicts the results.

## 1.2 Alternatives Considered

Alternatives considered: a single binary "did it compile" gate. Ruled out because it can't distinguish a run that checked one file from one that checked all of them, or a clear error report from a vague one -- and those differences are what I'd improve between runs.

## Scoring Guide

### Check Execution Accuracy

**1 - Does not meet:** Did not run the check, or reported results that don't match reality.
*Example: "The backend looks fine" with no py_compile run.*

**2 - Partially meets:** Ran the check but reported the outcome ambiguously.
*Example: "Mostly compiles" without saying which files or the real result.*

**3 - Meets:** Ran the check and accurately reported the real result.
*Example: "All 3 backend files compiled; app imported successfully."*

**4 - Exceeds:** Accurate result plus supporting evidence (the exact commands run and per-file outcomes).
*Example: Shows py_compile per file and the import command, with each result.*

### File Coverage

**1 - Does not meet:** Most backend files were not checked.
*Example: Only app.py checked; test_mysql.py and test_sms.py ignored.*

**2 - Partially meets:** Some files checked, at least one omitted.
*Example: app.py and test_mysql.py checked; test_sms.py not mentioned.*

**3 - Meets:** Every backend source file (excluding venv) is accounted for.
*Example: app.py, test_mysql.py, test_sms.py all reported pass/fail.*

**4 - Exceeds:** All files accounted for, with the file list explicitly enumerated so nothing is ambiguous.
*Example: Lists each .py file found and its individual result.*

### Error Reporting Clarity

**1 - Does not meet:** Failures reported with no file or error detail (or failures missed).
*Example: "Something failed to import."*

**2 - Partially meets:** Names the file or the error, but not both.
*Example: "app.py had an error" with no message.*

**3 - Meets:** Each failure names the file and includes the actual error; or a clean explicit all-passed statement.
*Example: "All files passed, no errors." OR "test_sms.py: ModuleNotFoundError: twilio."*

**4 - Exceeds:** Failures include file, error, and a brief note on likely cause; clean runs confirm what was verified.
*Example: "All 3 files compiled and app imported; verified no import-time or syntax errors."*

### Recommendation Quality

**1 - Does not meet:** No recommendation, or one that contradicts the results.
*Example: "Ready to proceed" after reporting an import failure.*

**2 - Partially meets:** A recommendation is given but is vague or not tied to results.
*Example: "Probably fine."*

**3 - Meets:** Clear recommendation consistent with the results.
*Example: "All files compile and import; safe to proceed."*

**4 - Exceeds:** Clear recommendation with specific next steps if any issues exist.
*Example: "Safe to proceed; note test_sms.py needs the twilio package installed to import."*

## Pass Threshold

A run is passing if it scores 3 or higher on all dimensions.

Reasoning: An import/compile check is only trustworthy if the agent actually ran it, covered every file, reported failures clearly, and gave a sound recommendation. A weakness in any one makes the "all clear" unreliable, so a dimension floor is appropriate.

## Threshold → Business Outcomes

The pass floor is tied to the Module 1 baseline: the import/compile check cost ~8 minutes of human review and ~$0.26 in tokens at 16/16 quality. The thresholds decide when "the backend is runnable" can be trusted without a human re-check — below the floor, a person must re-verify, so the saving is not claimed.

Check Execution Accuracy (3+): The check actually ran, so "the backend builds" is a verified fact, not a guess — downstream work isn't started on a broken base (avoids wasted cycles and a failed deploy).
File Coverage (3+): Every backend file is checked, so no un-compiled file slips through — prevents a broken module reaching deploy.
Error Reporting Clarity (3+): A failure names the file and the actual error, so the fix is immediate rather than a debugging hunt — keeps cycle time down.
Recommendation Quality (3+): The runnable/not-runnable call distinguishes an incidental standalone-script import failure (e.g. test_sms.py's live-call-at-import) from a real app break — avoids both false blocks (wasted time) and false "all clear" (a broken backend shipped).

Gate outcome: 3+ on all four → the backend's runnability is confirmed without a human pre-flight re-check → removes that ~8-minute / ~$0.26-per-run step. Below the floor keeps the human in the loop, so no saving is counted.


## Notes on Threshold Design

Considered an aggregate minimum (12/16). Ruled out because a run that skipped files (low File Coverage) could still pass on points while giving a false sense of safety. The dimension floor prevents a confident-but-incomplete check from passing.
