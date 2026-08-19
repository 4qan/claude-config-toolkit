---
description: Structural audit of Claude config (CLAUDE.md, skills, commands, references, memory) for duplication, conflicts, scope leaks, dead refs, and orphans. Three phases: scope, audit, apply.
---

Audit Claude configuration structure. $ARGUMENTS

## What /audit-config is (and is not)

**Is:** A structural audit skill that inspects a defined target (global config, a project, a single command, or a file) and reports duplication, conflicts, scope leaks, dead references, orphans, and inventory gaps. Produces a plan; applies fixes only after explicit approval.

**Is not:** A design review of whether a command is well-built. Not a judgment on whether instructions are "good." Not a dynamic flow tracer (instruction loading in Claude is non-deterministic; static cross-reference is the tractable frame).

**Relationship to `/reflect`:** `/reflect` is reactive and session-driven (a preference recurred; where did it drop?). `/audit-config` is proactive and target-driven (this artifact has accumulated; is it still coherent?). Both use the intervention hierarchy from the bundled `diagnostic-framework.md` when proposing fixes.

## Argument forms

| Form | Target |
|---|---|
| `global` | `~/.claude/CLAUDE.md` plus every file it references plus global memory index |
| `project [path]` | `<path>/CLAUDE.md` plus referenced files (path defaults to cwd) |
| `command <name>` | A slash command resolved by name, walked with every file it loads, references, or depends on. **Resolution order:** (1) `./.claude/commands/<name>.md` (project-local; this is the dev-loop location when working on a plugin from cwd), (2) `~/.claude/commands/<name>.md` (user-global), (3) `~/.claude/skills/<name>/` (user-global skill), (4) any plugin clone path discoverable via project config (e.g., a project config file that records a plugin clone path). If multiple resolve, list them and ask. |
| `agent <name>` | A subagent resolved by name. **Resolution order:** (1) `./.claude/agents/<name>.md` (project-local), (2) `~/.claude/agents/<name>.md` (user-global), (3) plugin agents discoverable via project config. Same multi-resolve handling as `command`. |
| `file <path>` | A single file in isolation (no dependency walk). Use this when `command`/`agent` resolution can't find the file (e.g., a plugin clone the project config doesn't reference). |
| `--apply <report-path>` | Phase 2: read approved findings from a prior Phase 1 report and apply fixes |

If arguments are missing or ambiguous, ask once. Do not guess the target. When `command <name>` or `agent <name>` resolves to a project-local file, note in the scope report that this is a dev-loop copy and that a plugin-shipped sibling may exist; the user may want to audit that too.

## Phase routing

- If `$ARGUMENTS` starts with `--apply`, jump to **Phase 2**.
- Otherwise, run **Phase 0 then Phase 1** in sequence, stopping between phases for confirmation only at Phase 0.

## Phase 0: Scope (always runs; fast)

**Goal:** enumerate everything in scope and let the user prune before Phase 1 burns context on the wrong files.

1. Based on the argument form, build the dependency tree:
   - Start from the target file(s).
   - Walk explicit references (`@path`, "see X", "Deeper reference: Y", file paths in prose).
   - For `command <name>` or `agent <name>`, also include: every file the command/agent Reads, every skill or subagent it invokes, every memory index entry relevant to it. If the resolved target is a project-local dev-loop file, also surface (but do not auto-walk) the plugin-shipped sibling path, if any, so the user can request a parallel audit.
   - Stop at depth 2 unless a referenced file itself has a dense outbound reference graph; note unexpanded nodes.
2. Print the tree as an indented list with short annotations (why this file is in scope).
3. State the audit scope explicitly: **"Auditing for config hygiene, not design quality."** If the user wants design review, redirect them.
4. Ask the user to confirm or prune before proceeding. Do not proceed silently.
5. Write `audits/{YYYY-MM-DD}-{target-slug}-scope.md` with the confirmed tree. Storage location:
   - Global / command / file targets: `~/.claude/audits/`
   - Project target: `<project>/audits/` (create if missing)

## Phase 1: Audit (run after Phase 0 is confirmed)

For each file in the confirmed scope, run the **seven checks** below. Judgment, not pure text matching. Flag with justification.

### The seven checks

| Check | Detects | Notes |
|---|---|---|
| **Inventory** | Every directive / rule / instruction the target defines, plus load path (auto-loaded at L3, referenced at L2, memory at L1, etc.) | Not a finding on its own; foundation for the other checks. |
| **Duplication** | The same rule **or canonical data** stated in two or more locations | Distinguish "echo for emphasis" (legitimate, e.g. a meta-rule repeated in its invocation site) from "competing sources of truth" (violates Reference > Duplicate). Only flag the second. See "Duplication: what counts" below for concrete patterns; do not bias toward textually-identical rule statements. |
| **Conflict** | Two rules that contradict each other, or where the right interpretation is ambiguous | Include the exact quotes from both sources. |
| **Scope leak** | Project-specific content inside a global file, or global / universal content inside a project file | Check against any global-vs-project scope rule the user's `~/.claude/CLAUDE.md` defines, if present. |
| **Role boundary** | A file containing content whose home is another file's role (template carrying procedure rules, agent inlining canonical data, rubric defining rendering tokens) | Distinct from Duplication: the content may exist only once but at the wrong home. See "Role boundary: what counts" below. Often the largest structural finding category; surfaces what hygiene-via-density misses. |
| **Dead reference** | A pointer (`@path`, "see X", file path in prose) to a file that does not exist, has moved, or no longer contains the referenced content | Resolve every reference; do not assume. |
| **Orphan** | A file, section, or memory entry that nothing references and no workflow triggers | Opposite of dead reference. Check both directions. |

### Duplication: what counts (worked examples)

Duplication is not just textually-identical rule statements. It includes any case where the same canonical content exists in two or more places with different framings, where one place is meant to be the source of truth and the others summarize, mirror, or restate it. Common patterns to flag:

| Pattern | Flag when | Example |
|---|---|---|
| **Canonical data mirrored in a router file** | An auto-loaded router (CLAUDE.md, MEMORY.md) repeats a list, table, or values that have a canonical home in a referenced file | A project CLAUDE.md listing API error codes with their meanings, when those codes are canonical in `docs/errors.md`. The router should reference, not restate. |
| **Vocabulary or word lists in multiple files** | The same enumerable list (banned words, valid options, error codes, status names) appears verbatim or near-verbatim in two or more files | A banned-words list inlined in both a writing style guide and a lint prompt, where the two have already drifted by one word. |
| **Decision narrative duplicating canonical config** | Memory entries describe "current architecture" using filenames, layouts, or values that have a canonical home elsewhere | A memory entry titled "Current layout" containing a table of canonical file paths and their roles. The architecture doc is the source of truth; the memory entry repeats it. |
| **Procedure step inlining data** | A command or agent step lists static data inline (fixed thresholds, valid values) instead of reading the canonical data file | A command's "Step 3" inlining threshold values, when the same values live in a config file. |

**Test:** if updating the canonical file requires also updating these other places to stay correct, it's duplication, not legitimate echo. If removing the secondary mention reduces only word count and not enforcement, it's duplication.

**Counter-pattern (legitimate echo, do not flag):** A meta-rule restated at its invocation site for procedural reinforcement (e.g. "remember to update X after Y" near the step that does Y). The repeated content is a reminder, not a second source of truth.

### Role boundary: what counts (worked examples)

Role boundary is distinct from Duplication. Duplication asks "does this content exist in two places?" Role boundary asks "is this content at the right file's home given each file's stated job?" Content can be present exactly once and still be at the wrong home; that's the case this check exists for.

Common patterns to flag:

| Pattern | Flag when | Example |
|---|---|---|
| **Template file containing procedure or scoring rules** | A "template" or "output structure" file holds rule-prose, not just fill-in-the-blank skeletons | An output template's "Rules the example does not show" section listing validation rules and formatting guards. These belong in the spec (semantics) or the command (procedure), not the template. |
| **Agent file containing canonical data** | An agent's workflow inlines fixed values, thresholds, or a controlled vocabulary that has a canonical home elsewhere | An agent's step listing fixed threshold values inline instead of reading them from the config. |
| **Rubric / reference file containing rendering tokens** | A scoring rubric or reference inlines markdown formatting, emoji vocabulary, or output-section structure | A rubric defining "use a check mark for pass" or specifying output spacing. Rendering decisions belong in the output template. |
| **Reference doc carrying procedural workflow** | A reference / data file embeds "do X then Y" steps that belong in an agent or command | A criteria reference doc with a "verify these fields first" workflow. Workflow belongs in the command or agent. |

**Test:** would a maintainer naturally update this content alongside an edit to a *different* file's role? Would the content "make sense" living in another file in scope without losing meaning? If yes to either, the content is at the wrong home; propose a move.

**Counter-pattern (legitimate cross-file content, do not flag):** A small sub-block restated in a child file as a quick-reference (e.g., a one-line summary of a load-bearing constraint at the call-site). The child file's primary role still dominates; the cross-file content is a reminder, not a misplaced home.

**Severity guidance for role-boundary findings:**
- HIGH when the misplaced content is a substantial block (10+ lines) auto-loaded on every run.
- MEDIUM when the misplaced content is a paragraph or section in a hot-path file.
- LOW for short reminders that are technically misplaced but don't materially confuse the file's job.

### Finding format

Each finding is one block in the report:

```
### [SEVERITY] Short title
**Check:** {duplication | conflict | scope-leak | role-boundary | dead-ref | orphan}
**Locations:** file:line references
**Evidence:** verbatim quotes or paths
**Justification:** why this is a real finding, not a false positive
**Proposed fix:** concrete action, stated as an intervention level change per the hierarchy (e.g. "Consolidate to L3 in ~/.claude/CLAUDE.md; demote memory entry to reference-only")
**Approval:** [ ] apply  [ ] skip  [ ] defer
```

### Severity scale

| Severity | Meaning |
|---|---|
| CRITICAL | Active conflict, dead reference in an auto-loaded path, or a rule guaranteed to misfire |
| HIGH | SSOT violation through duplication, scope leak at L3, or stale content in active use |
| MEDIUM | Redundant but non-conflicting phrasing, orphan that may still be intentional, partial drift |
| LOW | Minor wording inconsistency, organization improvement, pointer that technically works but is unclear |

### Report structure

Write `audits/{YYYY-MM-DD}-{target-slug}-report.md`:

1. **Header:** target, scope (from Phase 0), timestamp, "auditing for config hygiene"
2. **Summary table:** count of findings by check type and severity
3. **Findings, grouped by check type** (all duplications, then all conflicts, then all scope leaks, then all role-boundary findings, then all dead refs, then all orphans). Within each group, order by severity.
4. **Appendix: Fix checklist grouped by file.** The same findings re-indexed by file, so Phase 2 can walk one file at a time.
5. **Meta:** what was not audited and why (unexpanded tree nodes, files explicitly pruned in Phase 0).

Do **not** modify any files in Phase 1. This phase is read-only.

### Phase 1 ground rules

- **Justify every finding.** Text-matching duplicates are not findings unless the duplication violates Reference > Duplicate. State why.
- **Escalation rule from the diagnostic framework applies.** If a proposed fix adds yet another instance of a rule at the same intervention level it already failed at, say so and refuse the fix; propose escalation instead.
- **Never invent line numbers.** Read files to cite accurately.
- **If confidence is low**, mark the finding MEDIUM or LOW and flag the uncertainty in Justification. Do not fabricate evidence.
- **Memory snapshots are point-in-time.** Note the timestamp and treat findings on memory as valid only for this snapshot.

## Phase 2: Apply (separate invocation, after user approves items)

Triggered by `/audit-config --apply <report-path>`.

1. Read the report at `<report-path>`.
2. Parse the Fix checklist appendix. Collect only items with `[x] apply`. Ignore `[ ] apply`, `[x] skip`, `[x] defer`.
3. For each approved item, in appendix order (one file at a time):
   - Read the target file.
   - Apply the proposed fix exactly as stated in the finding. If the fix requires judgment not specified in the finding, stop and ask rather than improvising.
   - **If the fix is a CRITICAL conflict or duplication rewrite** (i.e., the canonical wording, threshold, vocabulary, or rule was changed): record the **pre-change phrase** and a short **post-change phrase** for the residual-scan step (#5 below).
   - After each fix, note the before / after diff in memory for the summary.
4. Do **not** touch unapproved findings. Do not batch silent rewrites.
5. **Residual scan (after each CRITICAL rewrite, before moving to the next finding):** grep for the recorded pre-change phrase across **every file in the original scope** (not just the file just edited). Surface each remaining occurrence:
   - If the occurrence is in a code-block or in clearly-historical "Process Updates" framing, log as informational; do not auto-edit.
   - Otherwise, add a follow-up entry to the applied doc tagged `RESIDUAL-FROM-{finding-id}` with the file:line and the suspected stale phrasing. Ask the user whether to apply the same vocabulary swap to each occurrence, one by one. Do not silently rewrite; these are echo-sites the original finding may not have covered.
   - The purpose: rule-change fixes that rewrite the canonical home often miss echo-sites in summary sections, sibling files, or restating bullets. Catch them here, not in the next audit.
6. If a fix would touch a file outside the original scope, stop and ask.
7. Write `audits/{YYYY-MM-DD}-{target-slug}-applied.md`:
   - List of applied fixes with diffs
   - **Residual-scan results** for each CRITICAL rewrite: pre-change phrase, post-change phrase, list of remaining occurrences (with user disposition per occurrence)
   - List of skipped / deferred fixes
   - Any fixes that failed to apply, with reasons
8. Do not commit unless the user asks. Report unstaged changes.

## Output file naming

- Scope: `{date}-{target-slug}-scope.md`
- Report: `{date}-{target-slug}-report.md`
- Applied: `{date}-{target-slug}-applied.md`

Where `target-slug` is:
- `global` for global
- `project-{basename}` for project
- `command-{scope}-{name}` for a command or skill, where `scope` is `project` / `user` / `plugin` based on resolution
- `agent-{scope}-{name}` for a subagent (same scope rules)
- `file-{basename}` for a single file

The `{scope}` qualifier prevents collisions when the same command name exists at multiple scopes (e.g., a project-local dev-loop copy and a user-global or plugin-shipped sibling). If only one resolves, scope is still recorded for clarity.

## Model guidance

Phase 0 and Phase 1 benefit from stronger reasoning (judgment on duplication vs. emphasis, conflict interpretation). Phase 2 is mechanical. If the user is on a smaller model and running Phase 1, warn that findings may under-justify. Do not refuse to run.

## Meta-flow with `/reflect`

After running `/audit-config` and applying fixes, `/reflect` becomes more useful because the structural ground under recent sessions is cleaner. The inverse is also true: `/reflect` may surface a preference that drops because of a structural issue this skill would catch. Running them in sequence is a deliberate pattern, not a redundancy.

## Composes with `/audit-tokens`

Run hygiene first; `/audit-tokens --from <this-report>` reads the confirmed dependency tree and findings to run a token-efficiency pass on the cleaned-up surface. Token findings cross-reference unresolved hygiene findings to avoid breaking flows. The two commands are siblings, not interchangeable: hygiene asks "is this coherent?", tokens asks "is this efficient?". Each refuses to overreach into the other's frame.
