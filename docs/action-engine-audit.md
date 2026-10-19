# Silly V1 action-engine audit

## Request flow before this milestone

1. The C# overlay sends the final transcript to `atticus.py --wait`; it also starts `--fast` during speech for instant commands.
2. Both public paths use `deterministic_action()`: the typed registry first, then at most one previously approved typed shortcut. They do not call the historical convenience parser.
3. A request that is not fast is sent to Claude Code by `start_claude()` and `run()`.
4. The prior implementation exposed Claude's `Bash` tool with bypassed permissions. A heuristic `PreToolUse` hook classified command strings and could ask for approval, but it was not an allow-list.
5. Learned shortcuts were persisted as shell command strings and replayed with Git Bash. The `--shortcut` CLI endpoint also accepted a user-supplied shell command. Watchers could run shell expressions.

## Safety decision

The heuristic shell gate is not a typed authorization boundary. The action engine therefore handles the supported deterministic OS actions with schema-validated action objects. Claude's Bash access, command-string shortcut replay, free-form shortcut creation, and shell watchers are disabled from the user request path. The legacy replay and watcher functions are compatibility stubs and the `--unwatch` endpoint no longer kills processes. Claude retains only read-only web tools for unresolved requests; no AI output can invoke a local executable or shell command.

The active Claude subprocess also receives only the capability-accurate
text-only system prompt. Historical helper/automation instructions and the
pre-tool command hook are not attached to that subprocess, so an unresolved
request cannot revive a shell-backed legacy capability through prompt state.

The `--fast` process is part of the native hotkey path, so it is constrained
by the same rule. Unsupported phrases exit without executing a player, a
legacy shortcut, a provider request, or a shell command. This prevents a
partial transcript from becoming a side-effecting legacy operation.

## Preserved components

- C# transcript capture, overlay, timing, and Python launching remain unchanged.
- `winctl.apps`, `winctl.launch`, `winctl.place`, and Windows shell URL association are reused behind typed executors.
- Existing text/screen/web reasoning continues for unresolved requests, without local action tools.
- HTTP(S) dispatch rejects credentials, malformed host/port forms, control or
  whitespace characters, raw quotes, and Windows-style backslashes before a
  URL reaches a Windows association or known-browser shortcut.

## Limitations

- Legacy command-string shortcuts are intentionally not replayed. They are neither migrated nor interpreted.
- Automation integrations and shell watchers are not available through AI planning until they have typed action definitions and confirmation policies.
- The initial typed registry covers app launch, HTTP(S) URLs, Google/YouTube/Amazon searches, and window arrangement only.
