# Claude Config Toolkit

Three diagnostic slash commands for keeping a [Claude Code](https://docs.claude.com/en/docs/claude-code) configuration consistent, correct, and cheap to run as it grows.

A serious Claude Code setup accumulates fast: a global `CLAUDE.md`, per-project instructions, dozens of commands and skills, reference files, memory, hooks. Left alone, that surface drifts. Rules get restated in three places and quietly disagree. A reference points at a file that moved. The same preference keeps getting "fixed" and keeps coming back. Auto-loaded files balloon and every session pays for content it never uses.

These three commands treat config as a system to maintain, not a pile of markdown.

| Command | Question it answers | When to run |
|---|---|---|
| **`/reflect`** | A preference keeps recurring: where in the signal path did it drop, and what is the *right level* to fix it? | End of a session where something went wrong more than once |
| **`/audit-config`** | This config has accumulated: is it still internally consistent? | Periodically, or before a big change |
| **`/audit-tokens`** | This config is coherent now: is any of it needlessly expensive? | After `/audit-config`, on the cleaned-up surface |

## The core idea: stop stacking surface fixes

Most config maintenance is additive. A rule gets ignored, so you add another line telling Claude to follow it. That line gets ignored too, so you add a third. The pile grows; the behavior doesn't change.

The toolkit is built on one diagnostic model instead (`references/diagnostic-framework.md`):

**Signal path.** Every stated preference travels through five stations: *Stated to Loaded to Consulted to Applied to Gated*. When a rule fails, it dropped at exactly one of them. Adding another sentence only helps if the drop was at "Stated" and it almost never is.

**Intervention hierarchy.** Fixes rank by enforcement strength, from a throwaway verbal note (L0) up through memory, auto-loaded context, command steps, output styles, and finally a hook that fails the tool call (L5).

**Escalation rule.** If a preference recurs, the previous fix was at the wrong level. Move *up* one level. Refuse to add another fix at the level that already failed. A memory file that didn't work does not get repaired by a second memory file.

All three commands share this model, so their fixes are stated as *level changes* ("promote this from a memory note to a command step"), not as more prose.

## The commands

### `/reflect`
Diagnostic reflection on a session. Extracts the reusable learnings, checks whether each one has already been "fixed" before, and for anything recurring, traces the signal path to find the real drop point and escalates the fix one level. Refuses same-level re-adds. It diagnoses where the preference failed instead of just recording it.

### `/audit-config`
A three-phase structural audit (scope to audit to apply) of a target you choose: your global config, a project, a single command, or one file. Runs seven checks: inventory, duplication, conflict, scope leak, role boundary, dead reference, orphan. Produces a severity-ranked report of findings, each with evidence and a proposed fix. Applies nothing until you approve it, one file at a time, with a residual scan that catches stale echo-sites a rewrite left behind.

### `/audit-tokens`
A static token-efficiency pass that runs **after** `/audit-config`, on the surface it just cleaned. Four checks: model fit (is a mechanical skill pinned to an expensive model?), instruction density, load efficiency (eager-loaded content that could be lazy, hooks scoped too wide), and a two-sided cross-check against the hygiene report so a token cut never breaks a flow. Grounds every claim in real token counts from the bundled helper, not line counts. Refuses to run without a fresh hygiene report, on purpose.

The three compose: **`/audit-config` then `/audit-tokens`** for a full structural-then-efficiency sweep, with **`/reflect`** handling the reactive, session-driven case in between.

## Install

### As a plugin (recommended)
Clone this repo and point Claude Code's plugin loader at it, or add it to a marketplace you control. Commands are auto-discovered from `commands/`; the reference and helper script resolve under `${CLAUDE_PLUGIN_ROOT}`.

### Manual
Copy the pieces into your user config:

```sh
cp commands/*.md        ~/.claude/commands/
cp references/*.md      ~/.claude/references/
cp scripts/count_tokens.py ~/.claude/scripts/
chmod +x ~/.claude/scripts/count_tokens.py
```

Then `/reflect`, `/audit-config`, and `/audit-tokens` are available in any session.

### Token counting (optional but recommended)
`/audit-tokens` uses `scripts/count_tokens.py` to measure real token cost. It calls Anthropic's `count_tokens` endpoint when an API key is available (`ANTHROPIC_API_KEY`, `COUNT_TOKENS_API_KEY`, or the `env.ANTHROPIC_API_KEY` block in your Claude settings), and falls back to a char/4 approximation otherwise. Approximate figures are clearly tagged. Standard library only, no dependencies.

## Design notes

- **Nothing is applied without approval.** Every audit is read-only until you check off findings; the apply phase is a separate invocation.
- **Claims are grounded.** The token auditor refuses to argue from line counts. Findings cite files, lines, and measured tokens.
- **The commands know their own scope.** Hygiene refuses to do design review; tokens refuses to do hygiene. Each redirects rather than overreaching.
- **Portable.** No dependency on any personal setup beyond standard Claude Code locations. The one shared reference and the one helper script ship in this repo.

## Layout

```
claude-config-toolkit/
  commands/
    reflect.md         diagnostic reflection, escalates recurring feedback
    audit-config.md    structural hygiene audit (7 checks, 3 phases)
    audit-tokens.md    token-efficiency audit (4 checks, needs a hygiene report)
  references/
    diagnostic-framework.md   the signal-path + intervention-hierarchy model
  scripts/
    count_tokens.py    token measurement helper (stdlib only)
```

## License

MIT. See `LICENSE`.
