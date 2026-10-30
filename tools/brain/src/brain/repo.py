"""Where a repository keeps its text: the one object every brain function takes.

``Repo`` holds a root and the relative locations brain reads and writes. The defaults describe the
semi-systematic layout; another repository passes its own values. Nothing in brain derives a path
from its own file or from the environment.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

MARKERS = (".git", "justfile", "pyproject.toml")


@dataclass(frozen=True)
class Repo:
    root: Path
    knowledge: str = "knowledge"
    datasets: str = "catalog/datasets"
    experiments: str = "research/experiments"
    skills: str = ".claude/skills"
    code: tuple[str, ...] = ("src", "research/signals")
    index_dir: str = ".index"
    index_md: str = "knowledge/INDEX.md"
    skip_parts: tuple[str, ...] = ("templates", ".obsidian", "__pycache__")

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", Path(self.root).resolve())

    @property
    def index_file(self) -> Path:
        return self.root / self.index_dir / "chunks.parquet"

    @property
    def index_md_path(self) -> Path:
        return self.root / self.index_md

    def path(self, rel: str) -> Path:
        return self.root / rel

    def rel(self, path: Path) -> str:
        """Repo-relative POSIX path, or the path as given when it is outside the root."""
        try:
            return Path(path).resolve().relative_to(self.root).as_posix()
        except ValueError:
            return Path(path).as_posix()

    def with_index_dir(self, index_dir: str | Path) -> Repo:
        return replace(self, index_dir=str(index_dir))

    @classmethod
    def discover(cls, start: Path | None = None, markers: tuple[str, ...] = MARKERS) -> Repo:
        """Walk up from ``start`` (default: the working directory) to the first folder holding one
        of ``markers``. Raises ``FileNotFoundError`` when none is found."""
        here = Path(start or Path.cwd()).resolve()
        for candidate in (here, *here.parents):
            if any((candidate / m).exists() for m in markers):
                return cls(candidate)
        raise FileNotFoundError(
            f"no repository root above {here} (looked for {', '.join(markers)})"
        )
