# Diagnostic Framework for Recurring Feedback

Used by `/reflect` (and any future diagnostic work) when analyzing user feedback or preferences that recur across sessions.

**Core premise.** Recurring feedback is not a knowledge problem (solved by adding more instructions). It is a signal-flow problem: an instruction exists but is not being consulted, applied, or enforced at the right layer. The right response is structural, not documentary.

## Signal Path

For any stated preference, the signal travels through five stations. The preference "dropped" at whichever station first answers no.

| # | Station | Question |
|---|---|---|
| 1 | Stated | Is the preference documented anywhere? |
| 2 | Loaded | Is it in auto-loaded context, or does it require an explicit Read? |
| 3 | Consulted | Does the task flow make me actually look at it, or is it background? |
| 4 | Applied | Did I follow the rule, or did my judgment misfire? |
| 5 | Gated | Is there a consequence for ignoring it, or is it advisory? |

## Intervention Hierarchy

Interventions rank by enforcement strength.

| Level | Mechanism | Strength characteristic |
|---|---|---|
| L5 | Hook (PreToolUse or PostToolUse) | Tool fails or warns without precondition; gates the write/tool surface, needs a tool call to fire |
| Output style | System-prompt conversational rules (`~/.claude/output-styles/`); set via `/config` then Output style, or the `outputStyle` field | Chat-surface ceiling (how Claude responds): applied every turn, resists context decay, above L3 |
| L4 | Mandatory step in the command or skill body | Part of the workflow, not general guidance |
| L3 | Auto-loaded context (CLAUDE.md line, MEMORY.md index) | Visible at session start; decays under context pressure, the output style does not |
| L2 | Referenced file pointed to by auto-load | Requires explicit Read |
| L1 | Memory file (not auto-loaded) | Surfaces only if looked for |
| L0 | Verbal instruction in conversation | Ephemeral |

**Skill-trigger caveat.** A skill body is L4 only once the skill is actually running. Reaching it by auto-invocation is unreliable: community-measured activation hovers around half the time, and all skill descriptions share a capped listing budget (skills past the cap are silently dropped from context entirely). Treat a skill as a deterministic *typed* command (`/name`), never as a reliable auto-trigger. Do not escalate a preference into a new skill expecting it to auto-fire, and prune the skill surface before adding to it.

## Failure Mode to Intervention Map

| Failure mode (drop station) | Wrong fix | Right fix |
|---|---|---|
| Not stated (1) | n/a | Document once at the right level (L2 or L3 depending on size) |
| Stated, not loaded (2) | Add another reference line | Promote to auto-loaded, or add a hook if content is large |
| Loaded, not consulted (3) | Repeat the rule louder | Mandatory step in the command/skill (L4), or hook (L5) |
| Consulted, not applied (4) | More abstract words | Pair rule with named concrete examples in the existing file |
| Applied, wrong interpretation (4) | More abstract words | Same: named examples, not more abstraction |
| Competing instructions (anywhere) | Add a third source | Audit, resolve, pick one SOT, make others reference it |

The right-fix levels above assume the **write/tool** ladder. For **chat-surface** rules (tone, length, format, stance), the output style replaces the L3/L4/L5 entries. Reach for a hook only when a tool call exists to gate.

## Escalation Rule

**If the same preference recurs, the previous intervention level was wrong. Move up one level. Refuse to add another intervention at the same level for the same preference.**

Same-level re-adds are the primary failure pattern of earlier reflection loops. A memory file that failed does not get fixed by another memory file. A CLAUDE.md line that failed does not get fixed by another CLAUDE.md line.

Branch on surface before moving up. A rule that fires in **chat** (tone, length, format, stance) escalates toward the output style, the system-prompt ceiling, and toward a hook only if there is a tool call to gate. A rule that fires on **writes/tool calls** (file contents, artifact shape) escalates toward a PreToolUse hook (L5). Pick the surface's ladder first, then move up one level on it.

## Conflict Audit Search Scope

Before writing a new instruction, grep for the topic across every surface that can influence future behavior:

- `~/.claude/CLAUDE.md`
- `~/.claude/output-styles/`
- `~/.claude/commands/`
- `~/.claude/skills/`
- `~/.claude/references/`
- `~/.claude/projects/*/memory/`
- All `./CLAUDE.md` files in project directories
- All `./.claude/commands/` and `./.claude/skills/` in project directories

If two or more sources cover the same topic and they differ, resolving the conflict (choose one SOT, make others reference it) is the fix. Adding a third voice is not.

## Application

The critical subset of this framework (signal path table, intervention hierarchy, escalation rule, failure map) is embedded directly in the `/reflect` command. That command does not require reading this file to function.

This file exists as deeper reference for cases where the embedded summary is insufficient, and as the citable anchor for future diagnostic work.
