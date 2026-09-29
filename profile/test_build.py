import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from collections import Counter
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
import charts  # noqa: E402

ROOT = build.ROOT
SYNTHETIC = "zebrafjord"


def synthetic_guard():
    return [(hashlib.sha256(SYNTHETIC.encode()).hexdigest(), len(SYNTHETIC))]


def pr(url, tier="A", proof=True, **kw):
    o, r, n = build.parse_url(url)
    item = {"url": url, "repo": f"{o}/{r}", "number": n, "title": f"fix {n}", "state": "MERGED",
            "author": "adi-IL", "merged_at": "2026-09-10T12:00:00Z", "merged_by": "copybara-service",
            "merge_oid": "a" * 40, "additions": 10, "deletions": 2,
            "stars": 5000, "tier": tier, "issue": "It broke.", "fix": "It works.",
            "proof": {"label": "testX", "path": "t.py", "line": 3,
                      "url": f"https://github.com/{o}/{r}/blob/{'a' * 40}/t.py#L3"} if proof else None}
    item.update(kw)
    return item


class GuardTest(unittest.TestCase):
    def test_catches_plain_and_obfuscated(self):
        terms = synthetic_guard()
        for text in ["see zebrafjord here", "Z.E.B.R.A-FJORD", "zebra fjord", "<b>ZebraFjord</b>"]:
            self.assertTrue(build.guard_hits(text, terms), text)

    def test_clean_text_passes(self):
        self.assertEqual(build.guard_hits("zebra and a fjord", synthetic_guard()), [])

    def test_repo_guard_file_parses(self):
        terms = build.load_guard(os.path.join(ROOT, "profile", "guard.txt"))
        self.assertEqual(len(terms), 4)
        self.assertTrue(all(len(d) == 64 for d, _ in terms))

    def test_tracked_text_files_are_clean(self):
        terms = build.load_guard(os.path.join(ROOT, "profile", "guard.txt"))
        for dirpath, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d != ".git"]
            for name in files:
                if name.endswith((".md", ".json", ".svg", ".py", ".yml", ".txt")):
                    path = os.path.join(dirpath, name)
                    with open(path, encoding="utf-8") as f:
                        self.assertEqual(build.guard_hits(f.read(), terms), [], path)


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.dir, "profile"))
        self.allow = {"owner": "adi-IL", "items": [
            {"url": "https://github.com/tensorflow/tensorflow/pull/1", "tier": "A", "issue": "i", "fix": "f"},
            {"url": "https://github.com/google/mug/pull/2", "tier": "B", "issue": "i", "fix": "f"},
        ]}
        with open(os.path.join(self.dir, "profile", "allowlist.json"), "w") as f:
            json.dump(self.allow, f)
        with open(os.path.join(self.dir, "profile", "guard.txt"), "w") as f:
            f.write(f"{synthetic_guard()[0][0]} {len(SYNTHETIC)}\n")
        self.write_readme("intro\n")

    def tearDown(self):
        shutil.rmtree(self.dir)

    def write_readme(self, intro):
        with open(os.path.join(self.dir, "README.md"), "w") as f:
            f.write(f"{intro}<!-- BEGIN:ledger -->\n<!-- END:ledger -->\n<!-- BEGIN:proofs -->\n<!-- END:proofs -->\n")

    def items(self):
        return [pr("https://github.com/tensorflow/tensorflow/pull/1"),
                pr("https://github.com/google/mug/pull/2", tier="B", merged_by="owner")]

    def read(self, name):
        with open(os.path.join(self.dir, name)) as f:
            return f.read()

    def test_renders_rows_proofs_and_card(self):
        build.build(self.dir, self.allow, self.items(), [], log=lambda m: None)
        readme = self.read("README.md")
        self.assertIn("#### TensorFlow · 1 merged", readme)
        self.assertIn("· merged ·", readme)
        self.assertNotIn("approv", readme.lower())
        self.assertIn("merged by @owner", readme)
        self.assertIn("<summary>All 2 merged fixes as text</summary>", readme)
        self.assertIn("[`testX`](https://github.com/tensorflow/tensorflow/blob/", readme)
        self.assertIn('srcset="assets/charts/projects-light.svg"', readme)
        self.assertIn('alt="Merged PRs by project: Mug 1, TensorFlow 1"', readme)
        for name in charts.render_all(self.items(), build.project):
            svg = self.read(name)
            ET.fromstring(svg)
            self.assertNotIn("approv", svg.lower())
        self.assertIn("2 OF 2 MERGED FIXES SHIP A REGRESSION TEST", self.read("assets/charts/proofs-dark.svg"))

    def test_banned_term_in_chart_label_is_caught(self):
        with mock.patch.dict(build.PROJECT_NAMES, {"google/mug": "Zebra Fjord"}):
            with self.assertRaises(build.BuildError):
                build.build(self.dir, self.allow, self.items(), [], log=lambda m: None)

    def test_renders_notes_and_guards_them(self):
        self.write_readme("intro\n<!-- BEGIN:notes -->\n<!-- END:notes -->\n")
        notes = {"essays": [{"title": "On caches", "url": "https://www.adityaai.dev/articles/x", "date": "2026-09-14"}]}
        with open(os.path.join(self.dir, "profile", "notes.json"), "w") as f:
            json.dump(notes, f)
        build.build(self.dir, self.allow, self.items(), [], log=lambda m: None)
        self.assertIn("- [On caches](https://www.adityaai.dev/articles/x) · Sep 2026", self.read("README.md"))
        notes["essays"][0]["title"] = "ZEBRA_FJORD"
        with open(os.path.join(self.dir, "profile", "notes.json"), "w") as f:
            json.dump(notes, f)
        with self.assertRaises(build.BuildError):
            build.build(self.dir, self.allow, self.items(), [], log=lambda m: None)

    def test_rejects_pr_link_outside_allowlist(self):
        self.write_readme("see https://github.com/google/gvisor/pull/14402\n")
        with self.assertRaises(build.BuildError):
            build.build(self.dir, self.allow, self.items(), [], log=lambda m: None)

    def test_rejects_banned_term_and_writes_nothing(self):
        before = self.read("README.md")
        items = self.items()
        items[0]["fix"] = "Z.ebra fjord"
        with self.assertRaises(build.BuildError):
            build.build(self.dir, self.allow, items, [], log=lambda m: None)
        self.assertEqual(self.read("README.md"), before)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "data", "ledger.json")))

    def test_live_check_drops_unmerged_and_foreign(self):
        allow = {"owner": "adi-IL", "items": [
            {"url": "https://github.com/a/b/pull/1", "tier": "A", "issue": "i", "fix": "f"},
            {"url": "https://github.com/a/b/pull/2", "tier": "A", "issue": "i", "fix": "f"},
            {"url": "https://github.com/a/b/pull/3", "tier": "A", "issue": "i", "fix": "f"},
        ]}
        fetched = {
            "https://github.com/a/b/pull/1": pr("https://github.com/a/b/pull/1"),
            "https://github.com/a/b/pull/2": pr("https://github.com/a/b/pull/2", state="CLOSED"),
            "https://github.com/a/b/pull/3": pr("https://github.com/a/b/pull/3", author="someone"),
        }
        with mock.patch.object(build, "fetch_pr", lambda url, tok: dict(fetched[url])), \
                mock.patch.object(build, "resolve_proof", lambda p, proof, tok: None):
            got = build.live_items(allow, "t", log=lambda m: None)
        self.assertEqual([p["number"] for p in got], [1])


class RepoOfflineTest(unittest.TestCase):
    def test_offline_render_matches_committed_readme(self):
        tmp = tempfile.mkdtemp()
        try:
            for part in ("README.md", "profile", "data", "assets"):
                src = os.path.join(ROOT, part)
                (shutil.copytree if os.path.isdir(src) else shutil.copy)(src, os.path.join(tmp, part))
            self.assertEqual(build.main(["--out", tmp, "--offline"]), 0)
            names = ["README.md", "data/ledger.json"] + sorted(
                os.path.join("assets", "charts", n) for n in os.listdir(os.path.join(ROOT, "assets", "charts")))
            self.assertEqual(len(names), 10)
            for name in names:
                with open(os.path.join(ROOT, name)) as a, open(os.path.join(tmp, name)) as b:
                    self.assertEqual(a.read(), b.read(), name)
        finally:
            shutil.rmtree(tmp)


def chart_values(svg, attr="data-value", kind=None):
    out = {}
    for el in ET.fromstring(svg).iter():
        if "data-label" in el.attrib and attr in el.attrib and (kind is None or el.get("data-kind") == kind):
            out[el.get("data-label")] = int(el.get(attr))
    return out


def expected(items):
    name = build.project
    counts = Counter(name(p["repo"]) for p in items)
    tested = Counter(name(p["repo"]) for p in items if p["proof"])
    adds, dels = Counter(), Counter()
    for p in items:
        adds[name(p["repo"])] += p["additions"]
        dels[name(p["repo"])] += p["deletions"]
    months = Counter(p["merged_at"][:7] for p in items)
    return counts, tested, adds, dels, months


class ChartNumbersTest(unittest.TestCase):
    def check(self, items):
        counts, tested, adds, dels, months = expected(items)
        svgs = charts.render_all(items, build.project)
        self.assertEqual(len(svgs), 8)
        for theme in charts.THEMES:
            get = lambda n: svgs[f"assets/charts/{n}-{theme}.svg"]
            self.assertEqual(chart_values(get("projects")), dict(counts))
            self.assertEqual(chart_values(get("proofs"), "data-total"), dict(counts))
            self.assertEqual(chart_values(get("proofs"), "data-tested"), {k: tested[k] for k in counts})
            self.assertEqual(chart_values(get("lines"), kind="additions"), dict(adds))
            self.assertEqual(chart_values(get("lines"), kind="deletions"), dict(dels))
            timeline = chart_values(get("timeline"))
            self.assertEqual(min(timeline), charts.TIMELINE_START)
            self.assertEqual({m: c for m, c in timeline.items() if c}, dict(months))
            self.assertEqual(sum(timeline.values()), len(items))
            total = sum(counts.values())
            self.assertIn(f"{sum(tested.values())} OF {total} MERGED FIXES", get("proofs"))
            self.assertIn(f"{total} TOTAL", get("projects"))
        return svgs

    def test_fixture_items(self):
        items = [pr("https://github.com/tensorflow/tensorflow/pull/1", merged_at="2026-09-02T00:00:00Z"),
                 pr("https://github.com/tensorflow/tensorflow/pull/2", proof=False, merged_at="2026-08-02T00:00:00Z",
                    additions=100, deletions=50),
                 pr("https://github.com/google/gvisor/pull/3", tier="B", merged_at="2026-09-20T00:00:00Z")]
        svgs = self.check(items)
        timeline = chart_values(svgs["assets/charts/timeline-dark.svg"])
        self.assertEqual(timeline, {"2026-07": 0, "2026-08": 1, "2026-09": 2})

    def test_every_chart_animates_once_and_respects_reduced_motion(self):
        with open(os.path.join(ROOT, "data", "ledger.json")) as f:
            items = json.load(f)["items"]
        durations = {"grow-x": 0.6, "grow-y": 0.6, "fade": 0.35, "draw": 0.9}
        for name, svg in charts.render_all(items, build.project).items():
            root = ET.fromstring(svg)
            style = "".join(el.text or "" for el in root.iter("{http://www.w3.org/2000/svg}style"))
            self.assertRegex(style, r"@keyframes \w", name)
            self.assertRegex(style, r"@media \(prefers-reduced-motion: reduce\) \{[^}]*animation: none", name)
            self.assertNotIn("infinite", style, name)
            animated = [el for el in root.iter() if el.get("class") in durations]
            self.assertTrue(animated, name)
            for el in animated:
                start = float(el.get("style", "animation-delay:0s").split(":")[1].rstrip("s"))
                self.assertLessEqual(start + durations[el.get("class")], charts.DURATION + 1e-9, name)
            data = [el for el in root.iter() if "data-label" in el.attrib]
            self.assertTrue(all(el.get("class") for el in data) or "proofs" in name, name)

    def test_charts_link_to_interactive_page(self):
        with open(os.path.join(ROOT, "README.md")) as f:
            readme = f.read()
        self.assertEqual(readme.count(f'<a href="{charts.INTERACTIVE_URL}"><picture>'), 4)
        self.assertEqual(readme.count("<picture>"), 5)

    def test_committed_charts_match_ledger(self):
        with open(os.path.join(ROOT, "data", "ledger.json")) as f:
            items = json.load(f)["items"]
        self.check(items)
        for name, svg in charts.render_all(items, build.project).items():
            with open(os.path.join(ROOT, name)) as f:
                self.assertEqual(f.read(), svg, name)


if __name__ == "__main__":
    unittest.main()
