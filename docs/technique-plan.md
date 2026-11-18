# Context-Management Technique Plan

## Explicit context boundary (at the Phase 1 -> Phase 2 transition)
At the boundary I will send a preamble that states: Phase 1 (public-facing prioritization) is
complete; Phase 2 will re-prioritize the SAME findings; the active constraint has CHANGED from
"internet-facing / public" to "internal-only behind VPN"; the finding list and their identities
from Phase 1 still matter and must be reused (not regenerated); and the Phase 1 ranked list is
the artifact being revised.
Why: the requirement change is the exact moment drift is most likely -- the agent could keep
applying the old "public-facing" severity logic to some findings while applying the new logic to
others. Restating current-vs-changed rules at the top of the turn anchors it to the new context.

## Proactive summarization (before introducing the change)
Right after Phase 1's ranked list is produced, and BEFORE I introduce the constraint change, I
will ask the agent to summarize: the current goal, the active rules, the findings and their
Phase 1 ranking (the artifact state), any open questions, and the next planned action. I will
verify the summary captures the ranked findings accurately before proceeding.
Why: the ranking is the thing Phase 2 must revise, so capturing it verbatim before the context
shifts protects it from drift/rot when the new constraint is layered on. It also gives a clean
record I can hand forward if the session were to continue in a fresh window.

## Compaction
I will use /compact only if the context window becomes crowded during the run. I do not plan to
force it; proactive summarization is the primary technique here and compaction is only a fallback.