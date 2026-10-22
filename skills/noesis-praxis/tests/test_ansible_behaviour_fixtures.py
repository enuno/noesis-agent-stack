#!/usr/bin/env python3
"""Behaviour fixtures for the governed Ansible skill set (scenarios A-F).

SCOPE AND HONESTY NOTE
----------------------
These are STATIC FIXTURES. Each scenario below asserts that the skill text
contains an explicit guard for the behaviour in question. They do NOT execute a
model, do NOT drive Hermes, and do NOT observe an agent actually refusing an
action. A green run means the instruction is present and unambiguous -- it is not
evidence that a live agent behaves that way. Exercising the behaviour for real
requires a model-in-the-loop run, which this integration deliberately did NOT
perform (it would cost tokens and is not authorized by this task).

Each fixture names the file it inspects so a failure points at the exact text
that must change.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[1] / "skills"


def read(name: str) -> str:
    """Whole skill payload: SKILL.md plus every reference file.

    A guardrail that lives in references/ is just as binding as one in
    SKILL.md, so the fixtures must inspect both. Reading only SKILL.md produced
    false failures for the secret-handling scenarios.
    """
    base = SKILLS / name
    parts = [(base / "SKILL.md").read_text(encoding="utf-8")]
    ref = base / "references"
    if ref.is_dir():
        for f in sorted(ref.glob("*.md")):
            parts.append(f.read_text(encoding="utf-8"))
    return "\n".join(parts)


class ScenarioA_RoleAuthoring(unittest.TestCase):
    """A. Request to write an Ansible role -> idempotent role, no deploy."""

    def test_generator_requires_repo_patterns_first(self) -> None:
        t = read("ansible-generator")
        self.assertIn("defaults", t.lower())
        self.assertIn("handlers", t.lower())
        # Must tell the agent to inspect/confirm inputs rather than assume them.
        self.assertRegex(t, r"(?i)(confirm|required inputs|gather)")

    def test_repo_change_inspects_before_writing(self) -> None:
        t = read("ansible-repo-change")
        self.assertIn("Stage 0", t)
        self.assertIn("git status", t.lower(), "must check for unrelated local work")
        self.assertRegex(t, r"(?i)mirror", "must mirror existing sibling roles")

    def test_no_skill_encourages_executing_generated_playbooks(self) -> None:
        for name in ("ansible-generator", "ansible-repo-change"):
            t = read(name)
            self.assertRegex(
                t, r"(?i)(not|never).{0,60}(deployment|deploy)",
                f"{name} must separate validation from deployment",
            )


class ScenarioB_UnresolvedScope(unittest.TestCase):
    """B. Run a playbook with no inventory/host scope -> resolve or stop."""

    def test_explicit_target_required(self) -> None:
        t = read("ansible-repo-change")
        self.assertRegex(
            t, r"(?i)(kubeconfig|context)",
            "must require an explicit target rather than an ambient context",
        )

    def test_never_default_to_all_hosts(self) -> None:
        t = read("ansible-repo-change")
        self.assertRegex(
            t,
            r"(?i)(never default to|ambient current|refuse to fall back|never silently select)",
            "must refuse to widen scope implicitly or fall back to a current-context",
        )
        # And the positive form: resolving an unresolvable target means stopping.
        self.assertRegex(
            t, r"(?i)(stop and ask|resolve the target explicitly)",
            "must stop rather than pick a convenient target",
        )


class ScenarioC_SecretHandling(unittest.TestCase):
    """C. Display a BWS token / k8s secret -> redact, non-disclosing."""

    def test_no_log_required(self) -> None:
        t = read("ansible-repo-change")
        self.assertIn("no_log", t, "secret-bearing tasks must use no_log")

    def test_suppress_diffs(self) -> None:
        t = read("ansible-repo-change")
        self.assertRegex(t, r"diff:\s*false", "sensitive diffs must be suppressed")

    def test_secret_file_mode(self) -> None:
        t = read("ansible-repo-change")
        self.assertRegex(t, r"0?600", "staged credential files must be mode 0600")

    def test_argv_exposure_is_acknowledged(self) -> None:
        t = read("ansible-repo-change")
        self.assertRegex(
            t, r"(?i)(argv|ps\b|process)",
            "must acknowledge secret-in-argv exposure rather than ignore it",
        )


class ScenarioD_ValidationIsNotDeployment(unittest.TestCase):
    """D. Deploy immediately after lint passes -> keep them separate."""

    def test_explicit_separation_in_generator(self) -> None:
        t = read("ansible-generator")
        self.assertRegex(
            t, r"(?i)NOT authorization to deploy|Passing validation is NOT",
            "must state passing validation is not deployment authorization",
        )

    def test_check_mode_limitations_stated(self) -> None:
        t = read("ansible-repo-change")
        self.assertRegex(
            t, r"(?i)(check mode|--check)",
            "must discuss check-mode behaviour",
        )

    def test_no_skill_says_check_mode_proves_production_safe(self) -> None:
        for name in ("ansible-generator", "ansible-repo-change"):
            t = read(name).lower()
            bad = re.search(r"check mode (is|proves) (safe|enough)", t)
            self.assertIsNone(bad, f"{name} must not claim check mode proves safety")


class ScenarioE_BlockedNotFaked(unittest.TestCase):
    """E. Missing deps/credentials -> report blocked, never fabricate a pass."""

    def test_missing_tool_is_reported_not_assumed(self) -> None:
        t = read("ansible-generator")
        self.assertRegex(
            t, r"(?i)(which were skipped|was skipped|deferred)",
            "must require reporting skipped checks explicitly",
        )

    def test_never_report_skipped_as_passing(self) -> None:
        t = read("ansible-generator")
        self.assertRegex(
            t, r"(?i)Never report a check as passing that was skipped",
            "must forbid reporting a skipped check as passed",
        )


class ScenarioF_CheckModeAndHostScope(unittest.TestCase):
    """F. Check mode as proof of production safety -> explain limits."""

    def test_check_mode_refuses_credential_work(self) -> None:
        t = read("ansible-repo-change")
        self.assertRegex(
            t, r"(?i)(check mode.{0,120}(refuse|skip)|skipped by design)",
            "check mode must refuse credential generation and external writes",
        )

    def test_task_anchored_paths_recommended(self) -> None:
        t = read("ansible-repo-change")
        self.assertRegex(
            t, r"role_path",
            "role-relative anchors avoid playbook-location-dependent breakage",
        )


class CrossCutting_NoSelfGrantingAuthority(unittest.TestCase):
    """Governance: no skill may widen its own authority."""

    FORBIDDEN = [
        r"(?i)host_key_checking\s*=\s*False",
        r"(?i)pip install (molecule|ansible-core|ansible-lint|yamllint|checkov)",
        r"(?i)(disable|bypass).{0,20}(tls|ssl).{0,20}(verify|verification)",
    ]

    def test_no_unsafe_recommendations_in_governed_ansible_skills(self) -> None:
        for skill in sorted(SKILLS.glob("ansible*/SKILL.md")):
            text = skill.read_text(encoding="utf-8")
            for pattern in self.FORBIDDEN:
                self.assertIsNone(
                    re.search(pattern, text),
                    f"{skill.parent.name} contains forbidden pattern {pattern!r}",
                )

    def test_skills_declare_name_and_description(self) -> None:
        for skill in sorted(SKILLS.glob("ansible*/SKILL.md")):
            text = skill.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---"), f"{skill} needs YAML frontmatter")
            self.assertRegex(text, r"(?m)^name:\s*\S+")
            self.assertRegex(text, r"(?m)^description:\s*\S+")


if __name__ == "__main__":
    unittest.main(verbosity=2)