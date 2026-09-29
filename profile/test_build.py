import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402

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
        self.assertIn("<summary>1 more merged fixes</summary>", readme)
        self.assertIn("[`testX`](https://github.com/tensorflow/tensorflow/blob/", readme)
        self.assertIn("1 TensorFlow", self.read("assets/ledger.svg"))
        self.assertIn("1 OF 1 SHIP A REGRESSION TEST", self.read("assets/ledger.svg"))
        self.assertNotIn("APPROV", self.read("assets/ledger.svg"))

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
            for name in ("README.md", "assets/ledger.svg", "data/ledger.json"):
                with open(os.path.join(ROOT, name)) as a, open(os.path.join(tmp, name)) as b:
                    self.assertEqual(a.read(), b.read(), name)
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
