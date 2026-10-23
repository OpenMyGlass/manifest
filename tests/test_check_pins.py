# SPDX-License-Identifier: Apache-2.0
"""tools/check_pins.py with a fake GitHub compare."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import check_pins  # noqa: E402


class CheckPinsTest(unittest.TestCase):
    JHEAD = "a97d4609993ed4391cdb63dd0ada0d37ace82dbe"

    def run_check(self, android, status, tag=JHEAD):
        calls = []

        def compare(repo, base, head):
            calls.append((repo, base, head))
            return status(repo)
        lines, problems = check_pins.check(android=android, compare=compare,
                                           tag_commit=lambda name, t: tag)
        return calls, lines, problems

    def test_every_github_project_is_compared_against_its_upstream(self):
        for android in ("4.4", "6.0"):
            with self.subTest(android=android):
                calls, _, problems = self.run_check(android, lambda repo: "behind")
                self.assertEqual(problems, [])
                self.assertTrue(calls)
                for repo, base, head in calls:
                    self.assertRegex(head, r"^[0-9a-f]{40}$")
                    self.assertTrue(base)
                device = ("OpenMyGlass/android_device_glass_glass-1",
                          check_pins.TRACKS[android]["device_branch"])
                self.assertIn(device, {(r, b) for r, b, _ in calls})

    def test_head_of_branch_passes(self):
        _, lines, problems = self.run_check("6.0", lambda repo: "identical")
        self.assertEqual(problems, [])
        self.assertTrue(all(line.startswith("ok   ") for line in lines))

    def test_pin_off_its_branch_fails(self):
        for status in ("ahead", "diverged", "error 404"):
            with self.subTest(status=status):
                _, lines, problems = self.run_check(
                    "6.0", lambda repo: status if repo == "OpenMyGlass/android_build" else "behind")
                self.assertEqual(len(problems), 1)
                self.assertIn("build:", problems[0])
                self.assertIn(status, problems[0])


    def test_aosp_project_must_be_its_tag(self):
        _, lines, problems = self.run_check("6.0", lambda repo: "behind")
        self.assertIn("ok   external/jhead: a97d4609993e on platform/external/jhead "
                      "refs/tags/android-6.0.1_r81: identical", lines)
        _, _, problems = self.run_check("6.0", lambda repo: "behind", tag="0" * 40)
        self.assertEqual(len(problems), 1)
        self.assertIn("external/jhead", problems[0])


if __name__ == "__main__":
    unittest.main()
