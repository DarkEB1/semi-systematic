"""`just project`: the README comes from the template, passes the frontmatter rules, and the
folder is the one source of truth for an experiment's project."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


new_project = _load("new_project", ROOT / "scripts" / "new_project.py")
new_experiment = _load("new_experiment", ROOT / ".claude" / "skills" / "new-experiment" / "run.py")


def test_readme_from_template_has_id_equal_to_slug():
    text = new_project.readme_text(
        "em-carry", "EM carry", "DarkEB1", "2026-10-30", "Does carry mean-revert?"
    )
    assert text.startswith("---\nid: em-carry\ntype: project\n")
    assert "<!--" not in text and "<handle>" not in text and "YYYY-MM-DD" not in text
    assert "Does carry mean-revert?" in text


def test_bad_slugs_are_rejected():
    assert new_project.main(["experiments", "--dry-run"]) == 2
    assert new_project.main(["Bad_Slug", "--dry-run"]) == 2


def test_experiment_files_live_under_the_project():
    files = new_experiment.files_for(
        "x", "em-carry", "DarkEB1", "2026-10-30", "h", ["prices_daily:2026-10-30"], None, 0
    )
    assert set(files) == {
        "research/em-carry/experiments/2026-10-30-x/config.yaml",
        "research/em-carry/experiments/2026-10-30-x/run.py",
        "research/em-carry/experiments/2026-10-30-x/results.md",
        "research/em-carry/experiments/2026-10-30-x/figures/.gitkeep",
    }
    assert "project: em-carry\n" in files["research/em-carry/experiments/2026-10-30-x/config.yaml"]


def test_experiment_requires_an_existing_project(capsys):
    assert new_experiment.main(["xx", "--dry-run"]) == 2
    assert new_experiment.main(["xx", "--project", "no-such-project"]) == 2
    assert "just project" in capsys.readouterr().err
