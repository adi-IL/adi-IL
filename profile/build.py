#!/usr/bin/env python3
"""Build the generated blocks of the adi-IL profile README.

Standard library only. Reads public GitHub data, renders only URLs listed in
profile/allowlist.json, and writes README.md blocks, data/*.json and
assets/ledger.svg. New merged PRs that match the showcase rules go to
data/review.json and are never rendered.
"""
import argparse
import base64
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://api.github.com"
MIN_STARS = 1000
TRIVIAL_LINES = 5
PROJECT_NAMES = {
    "tensorflow/tensorflow": "TensorFlow",
    "google/gvisor": "gVisor",
    "grafana/grafana": "Grafana",
}
PROJECT_ORDER = ["tensorflow/tensorflow", "google/gvisor", "grafana/grafana"]
BOTS = {"copybara-service", "github-actions"}
PR_URL = re.compile(r"https://github\.com/([\w.-]+)/([\w.-]+)/pull/(\d+)")
MONO = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace"
SANS = "Satoshi, 'Cabinet Grotesk', system-ui, -apple-system, 'Segoe UI', sans-serif"
LIME = "#CAFF4A"


class BuildError(Exception):
    pass


def token():
    for name in ("GH_TOKEN", "GITHUB_TOKEN"):
        if os.environ.get(name):
            return os.environ[name]
    try:
        return subprocess.run(["gh", "auth", "token"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        raise BuildError("no GitHub token: set GH_TOKEN")


def request(method, url, body=None, tok=None, tries=4):
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(tries):
        req = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": f"Bearer {tok}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "adi-IL-profile-build",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (403, 429, 502, 503) and attempt < tries - 1:
                time.sleep(2 ** attempt * 5)
                continue
            raise BuildError(f"{method} {url}: HTTP {e.code}")
    raise BuildError(f"{method} {url}: out of retries")


def graphql(query, variables, tok):
    out = request("POST", f"{API}/graphql", {"query": query, "variables": variables}, tok)
    if not out or out.get("errors"):
        raise BuildError(f"graphql: {out and out.get('errors')}")
    return out["data"]


PR_QUERY = """
query($o: String!, $r: String!, $n: Int!) {
  repository(owner: $o, name: $r) {
    stargazerCount
    pullRequest(number: $n) {
      url title state mergedAt additions deletions
      author { login }
      mergedBy { login }
      mergeCommit { oid }
    }
  }
}"""

SEARCH_QUERY = """
query($q: String!) {
  search(query: $q, type: ISSUE, first: 100) {
    nodes { ... on PullRequest {
      url title mergedAt additions deletions
      repository { nameWithOwner stargazerCount }
    } }
  }
}"""


def parse_url(url):
    m = PR_URL.fullmatch(url)
    if not m:
        raise BuildError(f"not a PR URL: {url}")
    return m.group(1), m.group(2), int(m.group(3))


def fetch_pr(url, tok):
    o, r, n = parse_url(url)
    data = graphql(PR_QUERY, {"o": o, "r": r, "n": n}, tok)["repository"]
    pr = data and data["pullRequest"]
    if not pr:
        return None
    return {
        "url": pr["url"], "repo": f"{o}/{r}", "number": n, "title": pr["title"],
        "state": pr["state"], "author": (pr["author"] or {}).get("login"),
        "merged_at": pr["mergedAt"], "merged_by": (pr["mergedBy"] or {}).get("login"),
        "merge_oid": (pr["mergeCommit"] or {}).get("oid"),
        "additions": pr["additions"], "deletions": pr["deletions"],
        "stars": data["stargazerCount"],
    }


def resolve_proof(pr, proof, tok):
    """Permalink to the regression test at the commit that landed."""
    if not proof or not pr.get("merge_oid"):
        return None
    o, r = pr["repo"].split("/")
    got = request("GET", f"{API}/repos/{o}/{r}/contents/{proof['path']}?ref={pr['merge_oid']}", tok=tok)
    if not got or "content" not in got:
        return None
    text = base64.b64decode(got["content"]).decode("utf-8", "replace")
    for i, line in enumerate(text.splitlines(), 1):
        if proof["anchor"] in line:
            return {"label": proof["label"], "path": proof["path"], "line": i,
                    "url": f"https://github.com/{pr['repo']}/blob/{pr['merge_oid']}/{proof['path']}#L{i}"}
    return None


def live_items(allow, tok, log):
    """Live-check every allowlisted PR; drop anything no longer merged by the owner."""
    items = []
    for entry in allow["items"]:
        pr = fetch_pr(entry["url"], tok)
        if not pr or pr["state"] != "MERGED" or pr["author"] != allow["owner"]:
            log(f"drop {entry['url']}: not merged by {allow['owner']}")
            continue
        pr.update(tier=entry["tier"], issue=entry["issue"], fix=entry["fix"])
        pr["proof"] = resolve_proof(pr, entry.get("proof"), tok)
        if entry.get("proof") and not pr["proof"]:
            log(f"proof not found for {entry['url']}")
        items.append(pr)
    return items


def is_trivial(pr):
    return pr["additions"] + pr["deletions"] <= TRIVIAL_LINES or "typo" in pr["title"].lower()


def review_candidates(allow, tok):
    """Merged PRs that match the showcase rules but are not in the allowlist."""
    listed = {e["url"] for e in allow["items"]}
    q = f"is:pr is:merged author:{allow['owner']} -user:{allow['owner']}"
    out = []
    for node in graphql(SEARCH_QUERY, {"q": q}, tok)["search"]["nodes"]:
        if not node or node["url"] in listed:
            continue
        repo = node["repository"]
        if repo["stargazerCount"] < MIN_STARS or is_trivial(node):
            continue
        out.append({"url": node["url"], "title": node["title"], "repo": repo["nameWithOwner"],
                    "stars": repo["stargazerCount"], "merged_at": node["mergedAt"]})
    return sorted(out, key=lambda c: c["url"])


def month(ts):
    return datetime.strptime(ts[:10], "%Y-%m-%d").strftime("%b %Y")


def project(repo):
    return PROJECT_NAMES.get(repo, repo)


def credit(pr):
    if pr["merged_by"] and pr["merged_by"] not in BOTS:
        return f"merged by @{pr['merged_by']}"
    return "merged"


def row(pr):
    head = (f"**{pr['repo']} [#{pr['number']}]({pr['url']})** · {month(pr['merged_at'])}"
            f" · {credit(pr)} · `+{pr['additions']} −{pr['deletions']}`")
    fix = pr["fix"]
    if pr["proof"]:
        fix += f" [Test ↗]({pr['proof']['url']})"
    return f"{head}<br>\n**Issue** {pr['issue']}<br>\n**Fix** {fix}\n"


def grouped(items):
    groups = {}
    for pr in items:
        groups.setdefault(pr["repo"], []).append(pr)
    order = [r for r in PROJECT_ORDER if r in groups] + sorted(r for r in groups if r not in PROJECT_ORDER)
    return [(r, sorted(groups[r], key=lambda p: p["merged_at"], reverse=True)) for r in order]


def render_ledger(items):
    a = [p for p in items if p["tier"] == "A"]
    b = [p for p in items if p["tier"] == "B"]
    out = ['<img src="assets/ledger.svg" alt="Upstream ledger summary" width="100%">', ""]
    for repo, prs in grouped(a):
        out.append(f"#### {project(repo)} · {len(prs)} merged\n")
        out.extend(row(p) for p in prs)
    if b:
        out.append(f"<details>\n<summary>{len(b)} more merged fixes</summary>\n")
        for p in sorted(b, key=lambda p: p["merged_at"], reverse=True):
            out.append(row(p))
        out.append("</details>")
    return "\n".join(out)


def render_proofs(items):
    rows = [p for p in items if p["tier"] == "A" and p["proof"]]
    out = ["| Project | Fix | Regression test, at the commit that landed |", "|---|---|---|"]
    for repo, prs in grouped(rows):
        for p in prs:
            out.append(f"| {project(repo)} | [#{p['number']}]({p['url']}) {p['title']} "
                       f"| [`{p['proof']['label']}`]({p['proof']['url']}) |")
    return "\n".join(out)


def render_svg(items):
    a = [p for p in items if p["tier"] == "A"]
    b = [p for p in items if p["tier"] == "B"]
    parts = [f"{len(prs)} {project(r)}" for r, prs in grouped(a)]
    tested = sum(1 for p in a if p["proof"])
    e = html.escape
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="840" height="150" viewBox="0 0 840 150" role="img" aria-label="Upstream ledger: {e(', '.join(parts))} merged">
  <rect x="0.5" y="0.5" width="839" height="149" rx="14" fill="#09090b" stroke="#27272a"/>
  <circle cx="34" cy="36" r="4" fill="{LIME}"/>
  <text x="48" y="40" fill="{LIME}" font-family="{e(MONO)}" font-size="11" letter-spacing="2.6">UPSTREAM LEDGER · MERGED FIXES</text>
  <text x="28" y="88" fill="#fafafa" font-family="{e(SANS)}" font-size="30" font-weight="700">{e('  ·  '.join(parts))}</text>
  <text x="28" y="122" fill="#a1a1aa" font-family="{e(MONO)}" font-size="12" letter-spacing="1.2">{tested} OF {len(a)} SHIP A REGRESSION TEST UPSTREAM · +{len(b)} MORE MERGED FIXES</text>
</svg>
"""


def render_notes(notes):
    return "\n".join(f"- [{n['title']}]({n['url']}) · {month(n['date'])}" for n in notes["essays"])


def replace_block(text, name, body):
    start, end = f"<!-- BEGIN:{name} -->", f"<!-- END:{name} -->"
    pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pat.search(text):
        raise BuildError(f"README is missing the {name} markers")
    return pat.sub(lambda _: f"{start}\n{body}\n{end}", text)


def load_guard(path):
    terms = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                digest, length = line.split()
                terms.append((digest, int(length)))
    return terms


def guard_hits(text, terms):
    norm = re.sub(r"[^a-z0-9]", "", text.lower())
    hits = []
    for digest, length in terms:
        for i in range(len(norm) - length + 1):
            if hashlib.sha256(norm[i:i + length].encode()).hexdigest() == digest:
                hits.append((digest[:12], i))
                break
    return hits


def check_links(text, allow):
    listed = {e["url"] for e in allow["items"]}
    bad = sorted({m.group(0) for m in PR_URL.finditer(text)} - listed)
    if bad:
        raise BuildError(f"rendered PR links not in allowlist: {bad}")


def build(out, allow, items, candidates, log=print):
    readme_path = os.path.join(out, "README.md")
    with open(readme_path) as f:
        readme = f.read()
    readme = replace_block(readme, "ledger", render_ledger(items))
    readme = replace_block(readme, "proofs", render_proofs(items))
    notes_path = os.path.join(out, "profile", "notes.json")
    scan_inputs = ["profile/allowlist.json"]
    if os.path.exists(notes_path):
        with open(notes_path) as f:
            readme = replace_block(readme, "notes", render_notes(json.load(f)))
        scan_inputs.append("profile/notes.json")
    ledger = {"items": [{k: p[k] for k in ("url", "repo", "number", "title", "tier", "merged_at",
                                           "additions", "deletions", "merged_by",
                                           "merge_oid", "proof")} for p in items]}
    files = {
        "README.md": readme,
        "data/ledger.json": json.dumps(ledger, indent=2, ensure_ascii=False) + "\n",
        "data/review.json": json.dumps({"candidates": candidates}, indent=2) + "\n",
        "assets/ledger.svg": render_svg(items),
    }
    terms = load_guard(os.path.join(out, "profile", "guard.txt"))
    files_to_scan = dict(files)
    for name in scan_inputs:
        with open(os.path.join(out, name)) as f:
            files_to_scan[name] = f.read()
    for name, text in files_to_scan.items():
        if guard_hits(text, terms):
            raise BuildError(f"banned term found in {name}")
    check_links(readme, allow)
    for name, text in files.items():
        path = os.path.join(out, name)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            f.write(text)
    log(f"rendered {len(items)} items, {sum(1 for p in items if p['proof'])} proofs, "
        f"{len(candidates)} review candidates")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=ROOT)
    ap.add_argument("--offline", action="store_true",
                    help="re-render from data/ledger.json without network")
    args = ap.parse_args(argv)
    with open(os.path.join(args.out, "profile", "allowlist.json")) as f:
        allow = json.load(f)
    log = lambda m: print(m, file=sys.stderr)
    try:
        if args.offline:
            with open(os.path.join(args.out, "data", "ledger.json")) as f:
                cached = {p["url"]: p for p in json.load(f)["items"]}
            items = []
            for e in allow["items"]:
                if e["url"] in cached:
                    items.append(dict(cached[e["url"]], issue=e["issue"], fix=e["fix"]))
            with open(os.path.join(args.out, "data", "review.json")) as f:
                candidates = json.load(f)["candidates"]
        else:
            tok = token()
            items = live_items(allow, tok, log)
            candidates = review_candidates(allow, tok)
        build(args.out, allow, items, candidates, log)
    except BuildError as e:
        log(f"build failed: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
