from __future__ import annotations

import re
import shutil
from pathlib import Path


class ScriptPlotExporter:
    """Save notebook-era figures into a per-script output folder."""

    def __init__(self, script_path: str | Path):
        self.script_path = Path(script_path).resolve()
        self.repo_root = Path(__file__).resolve().parent.parent
        self.output_dir = (
            self.repo_root / "output" / self.script_path.parent.name / self.script_path.stem
        )
        self._cleared = False
        self._counts: dict[str, int] = {}

    def save(self, figure, name: str | None = None):
        if figure is None:
            return None

        if not hasattr(figure, "write_html"):
            raise TypeError(
                f"Cannot save plot '{name or 'figure'}' from {self.script_path.name}: "
                "figure does not expose write_html()."
            )

        if not self._cleared:
            if self.output_dir.exists():
                shutil.rmtree(self.output_dir)
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self._cleared = True

        stem = self._next_stem(name or "figure")
        output_path = self.output_dir / f"{stem}.html"
        figure.write_html(output_path, include_plotlyjs="cdn")
        return figure

    def _next_stem(self, raw_name: str) -> str:
        stem = slugify(raw_name)
        count = self._counts.get(stem, 0) + 1
        self._counts[stem] = count
        if count == 1:
            return stem
        return f"{stem}_{count}"


def build_plot_exporter(script_path: str | Path) -> ScriptPlotExporter:
    return ScriptPlotExporter(script_path)


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return slug or "figure"
