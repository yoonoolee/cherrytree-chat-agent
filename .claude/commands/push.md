# /push

Commit and push changes directly to the current branch.

## Branch setup (one-time, per developer)
Each developer has one persistent personal branch named after them (e.g. `avery`, `tim`).
- Never commit to `master` directly
- Never use the `dev` branch — it is obsolete
- Never create new branches — each developer uses their one persistent branch indefinitely

## Steps

1. Run `git pull` to sync with remote. If there are merge conflicts, stop and tell the user to resolve them first. If nothing to commit and nothing to push, tell the user and stop.

2. Run `git diff HEAD` to understand the changes. Read the full diff — base the commit message on what actually changed, not just on what was worked on in the current session.

3. Draft a concise commit message (imperative mood, under 72 chars, "why" not "what"). Show it to the user and wait for approval before continuing.

4. Stage and commit with the approved message. Never include Claude attribution, co-author lines, or generated-with footers:
   ```
   git add -A && git commit -m "<approved message>"
   ```

5. Push to the current branch:
   ```
   git push
   ```
   If no upstream is set: `git push -u origin <branch>`. Never create a new branch or switch branches.
