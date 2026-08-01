---
name: pr-body-from-template
description: Whenever creating a PR for the user, first look for a
  pull_request_template.md in the target repo and fill it in fully — a summary
  paragraph, a reviewer's guide, and every checklist item ticked with a
  justification (never left blank, never silently ticked). Applies to every PR
  Claude creates, in any repo. Triggers "open a PR", "create a PR",
  "gh pr create", "push and open a PR".
---

# pr-body-from-template — fill the repo's PR template on every PR

Every repo can ship a `.github/pull_request_template.md`. When Claude creates
a PR, it MUST fill this template in full rather than write a freeform PR body
that ignores it. This applies unconditionally — the user should never have to
ask "did you fill the checklist?".

## Trigger

Before running `gh pr create` (or handing the user a web URL to open a PR),
read this skill and follow it. Trigger words: "open a PR", "create a PR",
"push and open the PR", "gh pr create", "PR body".

## Procedure

1. **Locate the template.** In the target repo, check these paths, in order,
   and use the first one that exists:
   - `.github/pull_request_template.md`
   - `.github/PULL_REQUEST_TEMPLATE.md`
   - `.github/PULL_REQUEST_TEMPLATE/*.md` (multiple templates — pick the one
     whose filename matches the branch's Jira/issue prefix, or ask the user
     if it's ambiguous)
   - `docs/pull_request_template.md`
   - Root `PULL_REQUEST_TEMPLATE.md`

   If none exists, write a plain PR body with these sections: **What / Why**,
   **How to review**, **Testing done**. Skip the checklist step.

2. **Read the template verbatim.** Preserve section headings, checkbox order,
   and any embedded links. Do not omit sections; do not reorder them.

3. **Fill the narrative sections** ("What is this PR for", "Reviewers Guide",
   or equivalents) based on:
   - The commit messages on the branch:
     `git log --oneline origin/<base>..HEAD`
   - The diff summary:
     `git diff --stat origin/<base>..HEAD`
   - The Jira / issue ID in the branch name or commit messages (usually
     `<PROJECT>-<num>`; link it as
     `https://cloudera.atlassian.net/browse/<PROJECT>-<num>` for Cloudera
     work, or the standard tracker URL for other orgs).

   Write in the same tone the surrounding narrative uses (technical, terse).
   Do not pad with adjectives. Prefer bullet lists over long paragraphs for
   file-by-file callouts.

4. **Answer every checklist item explicitly.** For each `- [ ] ...` line in
   the template:
   - Tick `- [x]` only when there is a defensible reason. Never tick
     silently.
   - When a checkbox is **N/A** (e.g. "run `make build`" on a docs-only PR),
     tick it AND add a one-line justification underneath, indented two
     spaces so the bullet nests visually:
     ```
     - [x] I have run `make build` successfully on my local machine.
       - N/A — docs-only PR; no compilable source touched.
     ```
   - When a checkbox is **not satisfied**, leave it unchecked AND explain
     why under the line, plus a remediation plan:
     ```
     - [ ] I have added automated tests for this change.
       - Not satisfied — <reason>. <what will happen instead: manual test
         plan, follow-up ticket, deferred to <PR>, etc.>
     ```
   - When a checkbox references a specific action the branch actually did
     (added tests, ran `make build`, changed dependencies), state exactly
     what was done:
     ```
     - [x] I have added automated tests for this change.
       - Added `pkg/foo/bar_test.go` (12 cases); all pass under
         `go test ./pkg/foo/...`.
     ```

   The output should let a reviewer skim only the checklist and understand
   the PR's risk surface without opening the diff.

5. **Draft-first.** Print the full PR body to the user in a fenced Markdown
   block BEFORE running `gh pr create`. Wait for their confirmation (or
   corrections). Do not open the PR until they say go.

6. **Open the PR.** Use `gh pr create` with a body file to preserve
   formatting including nested backticks and code fences. Prefer:
   ```bash
   gh pr create --base <base> --title '<title>' --body-file /tmp/pr-body.md
   ```
   over `--body "$(...)"` because shell quoting of Markdown is fragile.

   When the target host is a GitHub Enterprise instance (e.g. Cloudera's
   `github.infra.cloudera.com`), prefix with `GH_HOST=<host>`:
   ```bash
   GH_HOST=github.infra.cloudera.com gh pr create \
     --base develop-taikun \
     --title '<Jira>. <title>' \
     --body-file /tmp/pr-body.md
   ```

## Non-negotiables

- **Never** leave a checkbox blank when the template ships one.
- **Never** tick a checkbox with no justification. A silent tick is worse
  than an unchecked box because it looks like it was reviewed.
- **Never** invent test coverage. If the PR has no tests, either tick the
  "tests" checkbox with `  - N/A — <why>` or leave it unchecked with a
  reason. Do not claim tests exist that don't.
- **Never** open the PR before the user has seen the body. This is the
  single hardest rule to break by accident — put the draft in a fenced
  block and stop.

## Common patterns per checkbox family

- **JIRA / issue link.** Tick with the actual URL; extract from branch name
  or commit message. Prefer the exact form the template uses
  (`https://cloudera.atlassian.net/browse/DEX-nnnnn` for Cloudera work).
- **Tests.** Tick with `  - N/A — <why>` for docs / infra / build /
  workflow-only PRs. For code changes, list the test files added or state
  what was manually verified and why unit tests weren't feasible. Never
  claim manual testing was "extensive" without listing the specific
  scenarios.
- **`make build` / `make test` / equivalent.** Tick with `  - N/A — no
  <language> code changed; only <paths>` when the PR touches no compilable
  source. For code PRs, state the exact command run and its exit status.
- **Backward compatibility / upgrades.** Tick when the change is additive
  or purely a rename with all callers updated in the same PR. If a rename
  is done, name the specific caller updates.
- **Secrets / logging / API responses.** Read the diff for anything that
  looks like a credential, token, header, or environment variable. If in
  doubt, quote the specific line and reason about it.
- **Auth / authz.** Tick when the PR does not modify authentication
  middleware, RBAC, JWT handling, or session management. If it does, do
  not tick — flag that a pen-test review may be required.
- **Dependencies.** Tick when `go.mod`, `go.sum`, `pom.xml`, `package.json`,
  `requirements.txt`, `deps.env` are all untouched. If any are touched,
  list the exact modules added/upgraded and why.
- **Backup / CLI / build stability / APIs / public endpoints.** Domain-
  specific checkboxes; tick with a specific reason (e.g. "no changes to
  top-level Job or Resource structs" for backup, "no changes under
  pkg/api/" for APIs).

## Example (Cloudera CDH/dex template, docs-only PR)

For a PR that only touches `docs/security/`, every checkbox after "opened a
JIRA" typically gets a `  - N/A — docs-only, no <thing> changed` line, and
the JIRA link is the actual `DEX-nnnnn` URL from the branch name. The
DEX-22852 PR is a worked example — checklist items 3–14 all N/A with a
one-line reason each.
