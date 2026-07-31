---
name: jira-prioritize
description: Prioritize a set of Jira tickets (from a PDF export, a JQL manifest, or a pasted list) into P0/P1/rest tiers, applying a documented framework — blast radius × exploitability, discounted by compensating controls, adjusted for release-shaping impact. Emits a ranked table plus a cluster analysis of tickets that should be worked together. Use whenever the user asks to prioritize, rank, order, or triage a batch of Jira tickets, or asks "which of these matter for release X". Composes with the `jira-pdf-parse` skill for input.
---

# jira-prioritize

## When to use

Trigger this skill when the user's request is about ordering, ranking, prioritizing, or triaging a set of Jira tickets. Common phrasings:

- "Prioritize these Jiras"
- "Which of these matter for release X"
- "Rank these tickets"
- "Help me pick what to work on this sprint from <epic>"
- Any request that references a Jira PDF export and asks about relative importance

Do NOT trigger for:
- Single-ticket questions ("what does DEX-XXXX say").
- Requests to *categorize* tickets by field (labels, components) without a value judgment.
- Sprint planning that's purely about capacity, not priority.

## Framework this skill applies

Use these criteria, in this order:

1. **Blast radius** — cross-tenant identity forgery > cluster-wide privesc > VC-wide DoS > single-user metadata leak > docs.
2. **Exploitability** — "any authenticated user can do it" > "requires compromised pod first" > "requires SA token" > "requires prior RCE".
3. **Compensating controls** — before ranking a ticket high, check whether existing mesh policies, admission webhooks, AuthorizationPolicies, RBAC, or L4 mTLS already reduce the attack surface. If yes, discount the raw severity. This is the filter I got wrong on DEX-22180 earlier — don't skip it.
4. **Cost of fix vs. impact** — a ready-to-apply patch that closes a P0 gap outranks a large refactor that closes the same gap.
5. **Blockers / dependencies** — BLOCKED items are demoted regardless of severity; note the blocker inline.
6. **Cluster synergy** — group tickets that share a subsystem, chart, root cause, or reviewer so one sprint closes a whole class.
7. **Release-shaping impact** — if landing a single Jira unblocks a component's SAR/security review status (e.g. Conditional Approval → Approved), that's a strategic upgrade lever worth noting separately.

## Output shape

Produce exactly this structure. Do not add sections the user didn't ask for.

### 1. Train of thought (2–4 sentences)

State the criteria used and any project-specific weighting the user provided (e.g. "compensating controls per the SAR dossier"). Keep it terse.

### 2. Priorities table(s)

Two tables minimum: P0 (Must Do) and P1 (Very Important). Each row: `Jira | Component | Why now`.

If the user has specific priority-label semantics (e.g. "P0 = Must Do, P1 = Very Important, Rest = Important"), use those exact labels.

### 3. Rest (one-line reasons per ticket)

For every ticket NOT in P0/P1, one sentence explaining why it isn't higher — pointing at which criterion above pushed it down (compensating control? docs-only? DoS not confidentiality? blocked?).

### 4. Clusters

Named cluster list with the tickets in each and a one-sentence rationale — same chart, same reviewer, same admission-policy design, etc.

### 5. Optional: strategic levers

Only if the user provided release-shaping context (SAR dossier, GA plan, etc.). List single tickets whose completion moves a whole component's status.

## Instructions to Claude

1. **Parse first, prioritize second.** If the input is a PDF, invoke `jira-pdf-parse` and read only the compact JSON manifest. Do NOT `Read` the raw PDF or the `.txt` cache. If the user pastes a ticket list, work from that.

2. **Ask for release context if missing.** Prioritization without a target audience (this sprint? this quarter? GA? patch release?) is guesswork. If the request doesn't say, ask a single question via `AskUserQuestion` before ranking.

3. **Read companion docs the user cites.** If the user references a threat-model dossier, gap analysis, or SAR prep document, read it — that's where compensating-control claims and release-shaping context live. This is what makes the difference between a raw-severity ranking (wrong) and a residual-risk ranking (right).

4. **Always apply criterion #3 (compensating controls) explicitly.** Before promoting a ticket to P0, name the controls that would have to fail for the attack to succeed. If the controls make the attack require prior RCE / SA token / admin access, the ticket is not P0 unless the user says otherwise. Historical failure mode: overweighting worst-case-if-unmitigated instead of residual-after-mitigations.

5. **Match cluster boundaries to real work units** — a cluster is only useful if a single PR, a single reviewer, or a single design decision closes multiple tickets. "Same subsystem" alone isn't a cluster.

6. **Be prepared to defend and revise.** The user may push back with additional context (e.g. "you missed the compensating control"). Update the ranking without ego. Print only the delta from the previous version when correcting.

7. **Priority labels.** If the user's Jira instance uses non-standard labels (Must Do / Very Important / Important, or L/M/H), use their labels in the output tables rather than P0/P1/P2. Match user vocabulary.

## Compose with `jira-pdf-parse`

For any PDF input:

```bash
python3 ~/.claude/skills/jira-pdf-parse/parse.py <pdf> > /tmp/tickets.json
```

Then reason from `/tmp/tickets.json` — never from the raw PDF text.

For deep-dives on a single ticket during the ranking exercise:

```bash
python3 ~/.claude/skills/jira-pdf-parse/parse.py <pdf> --detail DEX-XXXX
```

## Common pitfalls (things I've gotten wrong before)

- **Ranking by raw threat description severity.** The ticket description is the *worst case*. The residual after compensating controls is the *real* priority. Always check both.
- **Treating docs-only tickets as low priority automatically.** A missing governance/exception Jira can be release-blocking even if there's no code to write. Check whether ProdSec/SAR is expecting the doc.
- **Treating "P1" or "Important" from the ticket itself as ground truth.** Ticket-level priority is set by the reporter at filing time and rarely reflects release-shaping impact. Re-rank from evidence.
- **Missing cluster synergy.** If four tickets share a fix template (e.g. AWC identity-header `remove:` in HTTPRoutes), calling that out saves the user significant sprint capacity vs. treating them as four independent items.
