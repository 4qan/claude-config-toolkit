---
description: Diagnostic reflection on session learnings. Escalates recurring feedback to the right intervention level instead of stacking surface fixes.
---

Reflect on this session using the diagnostic framework below. $ARGUMENTS

## What /reflect is (and is not)

This is **not** a classification machine that routes learnings into files. It is a **diagnostic skill** that traces where a preference dropped in the signal path, identifies the failure mode, and applies the right level of intervention.

Surface fixes (adding another memory line, another CLAUDE.md bullet) are the primary reason recurring feedback keeps recurring. This version refuses same-level re-adds.

## Framework (embedded)

### Signal path: five stations

Every preference travels through these stations. The first station that answers "no" is the drop point.

| # | Station | Question |
|---|---|---|
| 1 | Stated | Is the preference documented anywhere? |
| 2 | Loaded | Auto-loaded, or requires explicit Read? |
| 3 | Consulted | Did the task flow make me look at it? |
| 4 | Applied | Did I follow the rule, or did judgment misfire? |
| 5 | Gated | Is there a consequence for ignoring it? |

### Intervention hierarchy

| Level | Mechanism |
|---|---|
| L5 | Hook (PreToolUse or PostToolUse). Tool fails or warns without precondition. Gates the write/tool surface; needs a tool call to fire. |
| Output style | System-prompt-level conversational rules (`~/.claude/output-styles/`), applied every turn and resistant to context decay. The strongest home for **chat-surface** behavior (how Claude responds: tone, length, format, stance), above L3. Not for write-surface rules or project facts. Set via `/config` then Output style, or the `outputStyle` settings field. |
| L4 | Mandatory step in the command or skill body that produces the failing output. |
| | *L4 caveat: a skill/command body is L4 only when invoked. Auto-invocation is unreliable and the skill listing is budget-capped (overflow silently dropped). Count on `/name` typed invocation, never on auto-fire. Details: `diagnostic-framework.md`.* |
| L3 | Auto-loaded context (CLAUDE.md line, MEMORY.md index). Decays under context pressure; the output style does not. |
| L2 | Referenced file pointed to by auto-load (requires explicit Read). |
| L1 | Memory file (not auto-loaded). |
| L0 | Verbal instruction in conversation (ephemeral). |

### Escalation rule

**If the same preference recurs, the previous intervention level was wrong. Move up one level. Refuse same-level re-adds.**

Deeper reference: the bundled `diagnostic-framework.md` (installed at `~/.claude/references/diagnostic-framework.md` for a manual install, or `${CLAUDE_PLUGIN_ROOT}/references/diagnostic-framework.md` when installed as a plugin).

## Steps

### Step 1: Identify learnings

Extract each distinct preference, correction, or pattern from the session. Discard session-specific context (the specific bug, the specific draft). Focus on reusable signal.

If nothing worth saving, stop and say so. Do not force learnings.

### Step 2: Recurrence check (CRITICAL)

For each learning, grep for the topic across every influence surface:

- `~/.claude/CLAUDE.md`
- `~/.claude/output-styles/`
- `~/.claude/commands/`
- `~/.claude/skills/`
- `~/.claude/references/`
- `~/.claude/projects/*/memory/`
- All `./CLAUDE.md` in the current project tree
- All `./.claude/commands/` and `./.claude/skills/` in the current project tree

Match on intent, not literal phrase. "Don't use em-dashes" and "AI markers banned" are the same topic.

If matches found, this is **recurring feedback**. Go to Step 3. Otherwise, **novel preference**, go to Step 4.

### Step 3: Signal path trace (recurring feedback only)

Walk the five stations for the specific failing case:

1. **Stated:** Yes (Step 2 proved it). Note the file and the level (L1 through L4) where the prior intervention lives.
2. **Loaded:** Was the file auto-loaded, or a reference requiring Read?
3. **Consulted:** During the failing task, did the command flow force a Read of the rule? Or was it background context?
4. **Applied:** Did the output actually follow the rule, or did judgment misfire?
5. **Gated:** Was there a hook or tool-level consequence for ignoring the rule?

The first "no" is the drop point. The fix targets that station, **at one level higher than the prior intervention**.

First, ask **which surface the rule governs**. This picks the escalation path before you pick the level:

- **Chat surface** (how Claude responds: tone, length, format, stance): escalate toward the **output style**, the system-prompt-level ceiling. Reach for a hook only if there is an actual tool call to gate.
- **Write/tool surface** (file contents, command output, artifact shape): escalate toward a **PreToolUse hook (L5)**, which can fail or warn on the offending tool call.

Then move up one level along that surface's path:

| Prior intervention | Surface | Drop station | New intervention |
|---|---|---|---|
| L0 verbal / L1 memory | Chat | Not consulted | Output style (the chat-surface ceiling) |
| L3 CLAUDE.md line | Chat | Decays / not consulted | Output style |
| L1 memory file | Write | Not consulted | L3 auto-load, or L4 command step |
| L3 CLAUDE.md line | Write | Not consulted | L4 command step, or L5 hook |
| L4 command step | Write | Not applied | L5 PreToolUse hook (or concrete examples added to the consulted file) |
| L2 reference file | Write | Not loaded | L3 auto-load, or L5 hook |

**If the planned fix is the same mechanism as the prior fix (another memory entry, another CLAUDE.md line, another reference section), refuse it and escalate.**

### Step 4: Conflict audit

For each learning (novel or recurring), grep related keywords across the same surfaces as Step 2. If two or more sources cover the topic and they differ:

- Pick one as source of truth.
- Rewrite the others to reference the SOT.
- Do not add a third voice.

### Step 5: Match intervention level to failure mode

| Failure mode (drop station) | Right fix |
|---|---|
| Not stated (1) | Document once at L2 or L3 depending on content size. |
| Stated, not loaded (2) | Promote to auto-loaded, or add a hook if the content is too large to inline. |
| Loaded, not consulted (3) | Mandatory step (L4) inside the command/skill that produced the failing output, or hook (L5). |
| Consulted, not applied (4) | Pair the rule with named concrete examples (right-vs-wrong) in the file that is already being consulted. |
| Applied, wrong interpretation (4) | Same as above: named examples, not more abstraction. |
| Competing instructions | Resolve conflict, pick SOT. |

### Step 6: Confirm mechanism differs from prior fix

Before writing anything, answer this aloud: "What is the mechanism of my proposed fix, and is it at a higher level than any prior fix for the same topic?"

If the answer is "same mechanism type, new line in the same file type", **stop and escalate**. This is the single most important gate in this skill. Most past `/reflect` failures have been caused by skipping it.

### Step 7: Apply

Write the fix at the matched level. Verify it exists and is referenced correctly. Report what changed.

## Output format

After applying, report:

```
## Reflection Summary

**Learnings identified:** N
**Recurring (escalated):** N
**Novel (classified):** N

### Changes
- [Level Lx, file path]: [what] then [why this level was the right one]

### Refused (escalated instead)
- [learning]: same-level re-add rejected; escalated from Lx to Ly

### Skipped
- [learning]: [reason]
```
