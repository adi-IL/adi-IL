#!/usr/bin/env python3
"""Commit regenerated files through the GraphQL createCommitOnBranch mutation.

GitHub signs commits made this way, so the bot's commits show as Verified
without any private key in Actions. Only generated paths are committed, and
nothing is committed when they are unchanged.
"""
import base64
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

GENERATED = ["README.md", "data/ledger.json", "data/review.json", "assets/charts"]

MUTATION = """
mutation($input: CreateCommitOnBranchInput!) {
  createCommitOnBranch(input: $input) { commit { oid url } }
}"""


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def main():
    changed = [p for p in git("status", "--porcelain", "--", *GENERATED).splitlines() if p.strip()]
    paths = sorted({line[3:].strip() for line in changed})
    if not paths:
        print("no changes")
        return 0
    additions = []
    for path in paths:
        with open(path, "rb") as f:
            additions.append({"path": path, "contents": base64.b64encode(f.read()).decode()})
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    variables = {"input": {
        "branch": {"repositoryNameWithOwner": os.environ["GITHUB_REPOSITORY"],
                   "branchName": os.environ.get("PROFILE_BRANCH", "main")},
        "expectedHeadOid": git("rev-parse", "HEAD").strip(),
        "message": {"headline": f"chore(profile): refresh {day}"},
        "fileChanges": {"additions": additions},
    }}
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": MUTATION, "variables": variables}).encode(),
        headers={"Authorization": f"Bearer {os.environ['GH_TOKEN']}",
                 "User-Agent": "adi-IL-profile-build"},
        method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        out = json.load(resp)
    if out.get("errors"):
        print(f"commit failed: {out['errors']}", file=sys.stderr)
        return 1
    print(out["data"]["createCommitOnBranch"]["commit"]["url"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
