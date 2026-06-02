# Workflow
## Task Classification
On receiving any task, classify FIRST:

- **Trivial** (single file, <20 lines, no cross-file deps): Execute directly. No planning overhead.
- **Standard** (1-3 files, clear scope): Write 3-5 bullet plan inline, confirm with user, then execute.
- **Complex** (4+ files, architectural decisions, or ambiguous requirements): Invoke brainstorming → writing-plans → executing-plans skill chain. Write plan to `docs/plans/`.

When in doubt, classify UP. If execution diverges from the plan, STOP and re-plan — do not continue on a broken path.

## Ambiguity Protocol
When requirements are unclear:

1. State your best interpretation in one sentence
2. State the alternative interpretation(s)
3. Ask the user to pick — do NOT guess and build

Exception: if both interpretations lead to the same implementation, pick either and note your assumption.

## Delegation Contracts
Every Agent/Task call MUST include:
- Explicit input: what files/context the subagent needs
- Output contract: what it must return (format, keys, structure)
- Scope boundary: what it must NOT modify

After return: validate output against the contract before integrating. If it doesn't match, re-run with clarified instructions — do not manually fix subagent output.

## Communication
- Lead every response with what you DID, not what you're about to do (unless planning).
- When presenting choices, give a clear recommendation with reasoning — don't list options equally.
- If no tests exist for changed behavior, flag it: "No existing tests cover this change. Want me to add them?"
- During planning/brainstorming: be thorough — this is where detail pays off.
- Comments in code: single-line why-comments only. No what-comments. No decorative headers.
- **Verbosity:** Be maximally insightful in minimal words. Density over length — every sentence should carry signal. No filler, no restating the obvious, no padding. Preserve context window for iteration.