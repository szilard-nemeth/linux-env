#!/usr/bin/env python3
"""
Export a GitHub PR (metadata + issue comments + inline review threads) as a
single Markdown file. Works against enterprise GitHub via `gh api --hostname`.

Usage:
    ./gh-pr-export-md.py <owner/repo> <pr-number> [--host HOST] [--out FILE]

Defaults: --host github.infra.cloudera.com  --out pr<N>.md

Complements the `gh-pr-comments` shell function in ../git.sh, which dumps the
same data as plain text to stdout. This script produces a structured Markdown
file with PR metadata, a chronological timeline, and grouped inline threads
that link back to the GitHub anchors.
"""
import argparse
import collections
import datetime
import json
import subprocess
import sys


def gh(host, path, paginate=False):
    cmd = ["gh", "api", "--hostname", host, path]
    if paginate:
        cmd.append("--paginate")
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    if paginate:
        # --paginate concatenates arrays; each page is a separate JSON array; join them.
        # gh already merges array pages into one JSON array when the endpoint returns one.
        # Fall back to line-by-line JSON if that ever changes.
        return json.loads(out)
    return json.loads(out)


def ts(s):
    if not s:
        return ""
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M UTC")


def user(o):
    return (o.get("user") or {}).get("login", "?")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", help="owner/repo, e.g. CDH/dex")
    ap.add_argument("pr", type=int)
    ap.add_argument("--host", default="github.infra.cloudera.com")
    ap.add_argument("--out")
    args = ap.parse_args()

    now = datetime.datetime.now()
    time_fmt = now.strftime("%Y%m%d_%H%M%S")
    out_path = args.out or f"pr{args.pr}-{time_fmt}.md"
    url_base = f"https://{args.host}/{args.repo}/pull/{args.pr}"
    api_root = f"/repos/{args.repo}"

    print(f"Fetching {args.repo}#{args.pr} from {args.host} → {out_path}", file=sys.stderr)
    pr = gh(args.host, f"{api_root}/pulls/{args.pr}")
    issue_comments = gh(args.host, f"{api_root}/issues/{args.pr}/comments?per_page=100", paginate=True)
    review_comments = gh(args.host, f"{api_root}/pulls/{args.pr}/comments?per_page=100", paginate=True)
    reviews = gh(args.host, f"{api_root}/pulls/{args.pr}/reviews?per_page=100", paginate=True)

    L = []
    L += [
        f"# {pr['title']}",
        "",
        f"**PR:** [{url_base}]({url_base})  ",
        f"**Author:** @{user(pr)}  ",
        f"**State:** {pr['state']}{' (merged)' if pr.get('merged') else ''}  ",
        f"**Base → Head:** `{pr['base']['ref']}` ← `{pr['head']['ref']}` (`{pr['head']['sha'][:12]}`)  ",
        f"**Created:** {ts(pr['created_at'])}  |  **Updated:** {ts(pr['updated_at'])}  ",
        f"**Changed files:** {pr.get('changed_files','?')}  |  **+{pr.get('additions','?')} / −{pr.get('deletions','?')}**",
        "",
        "---",
        "",
        "## Description",
        "",
        pr.get("body") or "_(empty)_",
        "",
        "---",
        "",
        "## Timeline (issue comments + reviews, chronological)",
        "",
    ]

    timeline = []
    for c in issue_comments:
        timeline.append(
            dict(kind="comment", ts=c["created_at"], user=user(c), body=c.get("body", ""), url=c["html_url"])
        )
    for r in reviews:
        body = (r.get("body") or "").strip()
        state = r.get("state", "")
        if body or state:
            timeline.append(
                dict(kind="review", ts=r["submitted_at"], user=user(r), body=body, state=state, url=r["html_url"])
            )
    timeline.sort(key=lambda x: x["ts"] or "")

    for t in timeline:
        h = f"**REVIEW: {t['state']}**" if t["kind"] == "review" else "**Comment**"
        L += [f"### {h} — @{t['user']} · {ts(t['ts'])}", f"[link]({t['url']})", ""]
        L += [(t["body"] or "").strip() or "_(no body — state-only review)_", "", "---", ""]

    # Group inline review comments into threads
    by_id = {c["id"]: c for c in review_comments}

    def root_of(c):
        seen = set()
        while c.get("in_reply_to_id") and c["in_reply_to_id"] in by_id and c["in_reply_to_id"] not in seen:
            seen.add(c["in_reply_to_id"])
            c = by_id[c["in_reply_to_id"]]
        return c

    threads = collections.OrderedDict()
    for c in sorted(review_comments, key=lambda x: x["created_at"]):
        r = root_of(c)
        threads.setdefault(r["id"], []).append(c)

    L += ["## Inline review threads", ""]
    if not threads:
        L += ["_(no inline comments)_", ""]
    for rid, thread in threads.items():
        root = thread[0]
        path = root.get("path", "?")
        ln = root.get("line") or root.get("original_line") or "?"
        L += [f"### `{path}` : line {ln}", f"[thread]({root.get('html_url','')})", ""]
        for c in thread:
            L += [
                f"**@{user(c)}** · {ts(c['created_at'])} · [link]({c.get('html_url','')})",
                "",
                (c.get("body") or "").strip(),
                "",
            ]
        L += ["---", ""]

    with open(out_path, "w") as f:
        f.write("\n".join(L))
    print(f"Wrote {out_path} ({sum(1 for _ in L)} lines)", file=sys.stderr)


if __name__ == "__main__":
    main()
