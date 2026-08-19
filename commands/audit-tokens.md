---
description: Static token-efficiency audit of Claude config (model fit, instruction density, load-path efficiency). Sibling to /audit-config; requires a fresh hygiene report as input.
---

Audit Claude configuration for token efficiency. $ARGUMENTS

## What /audit-tokens is (and is not)

**Is:** A static efficiency audit on a target a hygiene audit just covered. Catches model-frontmatter mismatches, verbose phrasing, eager-loaded content that could be lazy, and hooks scoped too broadly. Produces a plan; applies fixes only after explicit approval.

**Is not:**
- A runtime profiler. Cannot tell you actual token cost without measurement.
- A model evaluator. Cannot guarantee a smaller model produces equivalent quality to a larger one for a given workload without testing.
- A guarantee that a "redundant" instruction won't break a flow. That's why a hygiene report is required input, and why this command refuses to run without it.
- A replacement for `/audit-config`. Hygiene findings (duplication, conflict, scope leak, dead ref, orphan) belong there. This command runs *after* hygiene on a cleaner surface.

**Relationship to `/audit-config`:** Hard dependency. `/audit-tokens --from <hygiene-report>` reads the confirmed dependency tree and findings, then runs efficiency checks on top of that shared context. Cross-references unresolved hygiene findings to avoid recommending fixes that would break flows.

**Relationship to `/reflect`:** `/reflect` diagnoses why preferences fail. This command diagnoses why config is expensive. Different evidence models; both feed into the intervention hierarchy in the bundled `diagnostic-framework.md`.

## Argument forms

| Form | Behavior |
|---|---|
| `--from <hygiene-report-path>` | **Required for Phase 0/1.** Reads the confirmed scope and findings from a prior `/audit-config` report. Runs on the same target. |
| `--apply <token-report-path>` | Phase 2: read approved findings from a prior token report and apply fixes. |

If `--from` is missing on a non-`--apply` invocation, refuse:

> `/audit-tokens` requires a fresh hygiene report as input. Run `/audit-config <target>` first, then re-invoke as `/audit-tokens --from <report-path>`. The hygiene report's dependency tree and unresolved findings are required to avoid breaking flows.

Do not infer a target. Do not reuse a stale report without confirming with the user.

## Phase routing

- If `$ARGUMENTS` starts with `--apply`, jump to **Phase 2**.
- Otherwise, require `--from`, then run **Phase 0 then Phase 1** in sequence, stopping between phases for confirmation only at Phase 0.

## Token measurement

This command grounds its claims in token counts via a helper script, not line counts. Line counts are a misleading proxy (a verbose comment costs less than a short table); claims like "saved 70 lines" don't translate to cost.

**Helper:** `count_tokens.py`, bundled with this toolkit (at `~/.claude/scripts/count_tokens.py` for a manual install, or `${CLAUDE_PLUGIN_ROOT}/scripts/count_tokens.py` when installed as a plugin).
- Uses Anthropic's `count_tokens` endpoint when an API key is available (via `ANTHROPIC_API_KEY`, `COUNT_TOKENS_API_KEY`, or the `env.ANTHROPIC_API_KEY` block in `~/.claude/settings.local.json` / `settings.json`).
- Falls back to a char/4 approximation otherwise. Approximate results are tagged `"method": "approx"` in the helper's JSON output and must be cited with the `~` prefix in the report (e.g., "~2,140 tokens").
- Stdlib only, no SDK dependency.

**Picking the model for each file:**
- Agent file (project `./.claude/agents/<name>.md`, user `~/.claude/agents/<name>.md`, or plugin `<plugin>/agents/<name>.md`): the agent's own `model:` frontmatter pin
- Command file (project `./.claude/commands/<name>.md`, user `~/.claude/commands/<name>.md`, or plugin `<plugin>/commands/<name>.md`): the command's own `model:` frontmatter pin, or the parent session's model if missing
- Reference docs read by an agent or command: the model of whatever loads them (if loaded by multiple consumers at different models, tokenize once per distinct model and cite both)
- CLAUDE.md and memory: parent session's model (the user's currently-running model)
- Frozen archives: skip tokenization unless the file is actually loaded in some path

The same scope resolution logic as `/audit-config` applies. If a hygiene report scoped a target as project-local (dev-loop) and a plugin-shipped sibling also exists, the token audit inherits that scope; it does not silently expand to the sibling.

**When to invoke the helper:**
- Once at end of Phase 0 over all in-scope files (baseline)
- Per finding in Phase 1 to compute `tokens_if_fixed`
- Once over changed files at end of Phase 2 (post-fix delta)

**Frontmatter-only fixes** (model-fit findings): skip token measurement; the cost claim is about model tier, not size.

## Phase 0: Scope (always runs; fast)

**Goal:** confirm the inherited scope before Phase 1 burns context.

1. Read the hygiene report at `--from <path>`. Extract:
   - The target (global / project / command / file)
   - The confirmed dependency tree from Phase 0 of the hygiene audit
   - All findings from Phase 1, with their severity and resolution state
2. Check freshness. If the hygiene report is older than 14 days OR if any file in the scope has been modified after the hygiene-report timestamp, warn the user and ask whether to proceed. Do not silently audit a stale snapshot.
3. Print the inherited scope as an indented list. Annotate against each file:
   - **Unresolved CRITICAL/HIGH hygiene findings**, these gate Phase 1's forward cross-check (NEEDS-HYGIENE-FIRST).
   - **Resolved CRITICAL hygiene findings** (especially conflict/duplication rewrites), these seed Phase 1's backward residual scan. Note the pre-change phrase from the hygiene-applied doc so Phase 1 can grep for echo-sites the apply phase may not have swept.
4. State the audit scope explicitly: **"Auditing for token efficiency, not config hygiene or design quality."** If the user wants either, redirect them.
5. Ask the user to confirm or prune. Pruning here means narrowing the inherited scope, not expanding it; if they want a wider scope, they need a new hygiene report.
6. **Tokenize all in-scope files** for baseline measurement. For each distinct (file, model) pair (see "Picking the model" above), invoke the helper with `<model> <files...>` and parse the JSON result. Note `default_method` from the response; if it's `approx`, every claim in this audit must use the `~` prefix.
7. Write `audits/{YYYY-MM-DD}-{target-slug}-tokens-scope.md` with the confirmed tree, a pointer to the source hygiene report, and a **Baseline token counts** table (path, model, tokens, method). Storage location matches the hygiene report's location:
   - Global / command / file targets: `~/.claude/audits/`
   - Project target: `<project>/audits/`

## Phase 1: Audit (run after Phase 0 is confirmed)

For each file in the confirmed scope, run the **four checks** below. Judgment, not pure text matching. Flag with justification and a static-confidence rating.

### The four checks

| Check | Detects | Notes |
|---|---|---|
| **Model fit** | `model:` frontmatter mismatched to the workload the description implies | Mechanical / templated / read-only work on a heavy model is a downgrade candidate. Complex synthesis on a light model is an upgrade candidate. Missing `model:` where the description gives a clear signal is a fix candidate. Do not flag missing `model:` when the workload is genuinely mixed. |
| **Instruction density** | Verbose phrasing reducible without info loss; redundant example sets; preambles that don't add enforcement | Distinguish "echo for emphasis" (legitimate, same logic as the hygiene audit) from "verbose by accident" (token waste). Only flag the second. The test: does removing the second mention reduce enforcement, or only word count? |
| **Load efficiency** | Eager-loaded content that could be reference-only; deep auto-load chains; hooks scoped too broadly | `@path` in CLAUDE.md to content not used every session is a candidate for "see X" reference instead. Hook matchers wider than necessary (`*` when `Edit` would do). Memory entries duplicating reference content. |
| **Hygiene cross-check** | **Two-sided.** (a) **Forward gate:** a proposed token-fix that would touch a file flagged as load-bearing or contested in an *unresolved* hygiene finding. Mark NEEDS-HYGIENE-FIRST and exclude from apply. (b) **Backward scan:** residuals of *resolved* hygiene findings, stale pre-change wording from CRITICAL rule rewrites that the hygiene apply didn't sweep across the full scope. Surface as standalone findings (severity inherited from the hygiene finding: CRITICAL to HIGH, HIGH to MEDIUM). | The forward gate prevents breaking flows; the backward scan catches what `/audit-config`'s apply phase may have missed. Common backward-scan target: a Phase-1 CRITICAL conflict fix that rewrote a canonical table; its echo-sites in summary sections, sibling files, and restating bullets often survive untouched. Grep for the pre-change phrase across every file in the inherited scope. |

### Finding format

Each finding is one block in the report. Mirrors `/audit-config`'s format with three added fields (`Static confidence`, `Token impact`, and the optional `NEEDS-HYGIENE-FIRST` flag):

```
### [SEVERITY] Short title
**Check:** {model-fit | instruction-density | load-efficiency}
**Locations:** file:line references
**Evidence:** verbatim quotes, frontmatter excerpts, or paths
**Justification:** why this is a real finding, not a false positive
**Static confidence:** HIGH (text/frontmatter only) | MEDIUM (judgment on density) | LOW (would benefit from runtime confirmation)
**Token impact:** baseline X tokens then predicted Y tokens (delta -Z tokens, on <hot-path|cold-path|every-spawn|empty-state>)
                  [or: N/A, frontmatter-only fix]
                  [prefix all numbers with ~ if measured via approx fallback]
**Proposed fix:** concrete action stated as an intervention level change per the hierarchy
**Hygiene cross-check:** clean | NEEDS-HYGIENE-FIRST: <hygiene-finding-id>
**Approval:** [ ] apply  [ ] skip  [ ] defer  [ ] confirm-low (required for LOW-confidence apply)
```

**Computing Token impact:**
- *Removal* fixes: tokenize the removed block via the helper with `<model> --stdin` (or write to a temp file). Delta is negative.
- *Replace* fixes: tokenize old block AND new block. Delta = old - new (negative if shrinking).
- *Split* fixes (move a section to a new file): hot-path delta (main file shrinks) AND cold-path delta (new file appears, only loaded conditionally). Cite both, label which path each applies to.
- *Reorder* fixes (lazy-load): no per-file size change; cite the per-run delta, the file size that's NOT loaded on the early-exit path.
- *Sign check*: if `Token impact` shows a positive delta on the hot path, the finding is not a saving; re-classify or drop.

### Severity scale

Same vocabulary as `/audit-config`. Calibration for token findings:

| Severity | Meaning |
|---|---|
| CRITICAL | Eager-loaded content that demonstrably never applies in normal sessions; `model:` set to a heavy model on a skill that only reads files; a hook that fires on every tool call but only acts on one |
| HIGH | Verbose phrasing that materially inflates a frequently auto-loaded file; hook matcher significantly broader than its purpose; missing `model:` on a high-traffic skill with a clear workload signal |
| MEDIUM | Density / phrasing improvements where the cut is judgment-heavy; lazy-load candidates that would help only some session shapes |
| LOW | Speculative model-fit suggestions; anything dependent on runtime confirmation; small phrasing tightening |

### Report structure

Write `audits/{YYYY-MM-DD}-{target-slug}-tokens-report.md`:

1. **Header:** target, scope (from Phase 0), source hygiene report path, timestamp, "auditing for token efficiency". Note the measurement method (`api` or `approx`); if approx, state that all token figures are prefixed with `~` and are directional.
2. **Baseline summary:** total tokens across the in-scope surface (table from the scope file, summed). This anchors the magnitude claims that follow.
3. **Summary table:** count of findings by check type, severity, and confidence; total predicted token delta (hot-path) at the bottom.
4. **Findings, grouped by check type** (model-fit, then instruction-density, then load-efficiency). Within each group, order by severity, then by `Token impact` magnitude (largest savings first within a severity tier), then by static confidence (HIGH before LOW).
5. **NEEDS-HYGIENE-FIRST list:** every finding gated on an unresolved hygiene finding, with the hygiene-finding ID and a one-line description.
6. **Appendix: Fix checklist grouped by file.** Same format as the hygiene audit so Phase 2 can walk one file at a time. Cite each item's `Token impact` summary alongside the checkbox.
7. **Meta:** files in scope where no findings were produced; what was not audited and why; measurement method.

Do **not** modify any files in Phase 1. This phase is read-only (tokenizing is read-only).

### Phase 1 ground rules

- **Justify every finding.** Token-cost claims need measured evidence; invoke the helper for the affected content. Line counts and "feels long" are not justifications.
- **Every density / load-efficiency finding has a `Token impact:` line.** Frontmatter-only model-fit findings are the only exception (mark `N/A, frontmatter-only fix`).
- **The hygiene cross-check is two-sided and runs on every file in scope.** (a) *Forward gate:* if the file has an unresolved CRITICAL or HIGH hygiene finding, the token finding ships with NEEDS-HYGIENE-FIRST and is excluded from Phase 2 until the hygiene finding is resolved. (b) *Backward residual scan:* for every **resolved** CRITICAL hygiene finding noted in Phase 0, grep every file in scope for the pre-change phrase. Each remaining occurrence becomes a standalone token finding (the fix is usually a short wording swap with near-zero token delta but a real correctness benefit); these findings often pay for themselves by surfacing stale wording the next hygiene audit would have caught only after another round-trip.
- **Escalation rule from the diagnostic framework applies.** If a proposed fix adds yet another instance of a token waste at the same intervention level it already failed at, propose escalation instead.
- **Never invent line numbers, frontmatter values, load paths, or token counts.** Read files and run the tokenizer to cite accurately. Inventing token figures is a CRITICAL failure mode of this command.
- **Confidence floor:** if a finding's evidence depends on knowing what tasks the skill actually performs at runtime, mark LOW. Token magnitude alone cannot promote a LOW finding to MEDIUM; runtime relevance is its own axis.
- **Do not propose fixes that hygiene already proposed.** If `/audit-config` flagged a duplication and the fix would also be a token win, reference the hygiene finding ID instead of re-flagging. (This avoids double-counting in the predicted-delta total.)

## Phase 2: Apply (separate invocation, after user approves items)

Triggered by `/audit-tokens --apply <report-path>`.

1. Read the report at `<report-path>`. Note the measurement method (`api` or `approx`); the post-fix re-measurement uses the same method.
2. Parse the Fix checklist appendix. Collect items with `[x] apply`.
3. **Refuse any item with NEEDS-HYGIENE-FIRST.** Tell the user which hygiene finding must be resolved first.
4. **Refuse any LOW-confidence item without `[x] confirm-low`.** Tell the user the item needs explicit confirmation given runtime uncertainty.
5. For each remaining approved item, in appendix order (one file at a time):
   - Read the target file.
   - Apply the proposed fix exactly as stated. If the fix requires judgment not specified in the finding, stop and ask rather than improvising.
   - After each fix, note the before / after diff for the summary.
6. Do **not** touch unapproved findings. Do not batch silent rewrites.
7. If a fix would touch a file outside the original scope, stop and ask.
8. **Re-tokenize all changed files** using the helper with the same model that was used for each file's baseline in Phase 0. Compare actual deltas against each finding's predicted `Token impact`.
9. Write `audits/{YYYY-MM-DD}-{target-slug}-tokens-applied.md`:
   - Applied fixes with diffs AND a `predicted -X / actual -Y / variance Z%` line per fix
   - **Variance flag:** if any fix's actual delta diverges from predicted by >5%, surface it as a callout. Common causes: the Edit changed more than the finding said (over-fix), the new content was longer than estimated, or a tokenizer disagreement. Investigate before trusting the report's totals.
   - Aggregate: total predicted savings vs total actual savings across all applied fixes.
   - Skipped / deferred / refused fixes (with reasons: NEEDS-HYGIENE-FIRST, missing confirm-low, etc.)
   - Any fixes that failed to apply, with reasons
10. Do not commit unless the user asks. Report unstaged changes.

## Output file naming

- Scope: `{date}-{target-slug}-tokens-scope.md`
- Report: `{date}-{target-slug}-tokens-report.md`
- Applied: `{date}-{target-slug}-tokens-applied.md`

`target-slug` matches the hygiene report's slug exactly (so the two reports sit adjacent in `audits/`).

## Model guidance

Phase 0 and Phase 1 benefit from stronger reasoning (model-fit and density judgments are not pure text matching). Phase 2 is mechanical. If running on a smaller model, Phase 1 findings may under-justify; warn but do not refuse.

## Meta-flow

- **With `/audit-config`:** required upstream. Run hygiene first, resolve CRITICAL/HIGH findings, then run this command with `--from`. The two reports together describe both the structural and efficiency state of the target.
- **With `/reflect`:** orthogonal. `/reflect` handles preference-recurrence diagnostics; this command handles cost diagnostics. Running them together is fine; they don't share evidence.
