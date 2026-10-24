import json
import os
import subprocess
import sys
import unittest

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")


def run(*args):
    env = dict(os.environ, PYTHONPATH=SRC + os.pathsep + os.environ.get("PYTHONPATH", ""), NO_COLOR="1")
    return subprocess.run([sys.executable, "-m", "actor_rosetta", *args], capture_output=True, text=True, env=env,
                          timeout=60)


class CliSmoke(unittest.TestCase):
    def test_lazarus_short_form(self):
        r = run("Lazarus")
        self.assertEqual(r.returncode, 0)
        self.assertIn("short form of 'Lazarus Group'", r.stdout)
        self.assertIn("ATT&CK G0032", r.stdout)
        self.assertEqual(json.loads(run("--json", "Lazarus").stdout)["match"]["type"], "short-form")

    def test_no_self_referential_warnings(self):
        for name in ("APT35", "Lazarus Group", "Magic Hound"):
            self.assertNotRegex(run(name).stdout, r"(?i)(\b\w[\w ]*) also used for \1\b")

    def test_version(self):
        r = run("--version")
        self.assertEqual(r.returncode, 0)
        self.assertRegex(r.stdout, r"^actor-rosetta \d+\.\d+\.\d+ \(data \S+\)\n$")

    def test_lookup_human(self):
        r = run("Cozy", "Bear")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("APT29", r.stdout)
        self.assertIn("G0016", r.stdout)
        self.assertIn("Midnight Blizzard", r.stdout)
        self.assertNotIn("\x1b[", r.stdout)

    def test_lookup_json(self):
        r = run("--json", "midnight blizzard")
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        self.assertEqual(d["attack_id"], "G0016")
        self.assertTrue(all(n["sources"] for n in d["names"]))

    def test_unknown_exit_code(self):
        r = run("zzzz-not-a-group")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout, "")
        self.assertIn("No data", r.stderr)

    def test_search(self):
        r = run("search", "Cozy Baer")
        self.assertEqual(r.returncode, 0)
        self.assertIn("APT29", r.stdout)
        self.assertEqual(json.loads(run("--json", "search", "Cozy Baer").stdout)[0]["attack_id"], "G0016")

    def test_list(self):
        r = run("list")
        self.assertEqual(r.returncode, 0)
        self.assertIn("G0016\tAPT29", r.stdout)
        self.assertGreater(len(json.loads(run("list", "--json").stdout)), 10)

    def test_explain(self):
        r = run("explain", "CL0P")
        self.assertEqual(r.returncode, 0)
        self.assertIn("ransomware", r.stdout)

    def test_no_args(self):
        r = run()
        self.assertEqual(r.returncode, 2)
        self.assertIn("usage", r.stderr)

    def test_empty_search_is_usage_error(self):
        r = run("search", "")
        self.assertEqual(r.returncode, 2)
        self.assertIn("usage", r.stderr)

    def test_unknown_option_is_usage_error(self):
        r = run("--bogus")
        self.assertEqual(r.returncode, 2)
        self.assertIn("unknown option", r.stderr)

    def test_garbage_gives_no_suggestions(self):
        for q in ("' OR 1=1 --", "search "):
            r = run(q)
            self.assertEqual(r.returncode, 1)
            self.assertNotIn("Closest", r.stderr)

    def test_broken_pipe_is_quiet(self):
        env = dict(os.environ, PYTHONPATH=SRC)
        p = subprocess.Popen([sys.executable, "-m", "actor_rosetta", "list", "--json"], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, env=env)
        p.stdout.read(10)
        p.stdout.close()
        err = p.stderr.read().decode()
        p.wait(timeout=60)
        self.assertNotIn("Traceback", err)

if __name__ == "__main__":
    unittest.main()
