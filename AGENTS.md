# STEER Agents.md

## Dev environment tips
- Use the `STEER` conda env for all Python work in `steer-opencell-data`
  (`conda activate STEER`).
- `steer_opencell_data/database.db` is stored with Git LFS — run
  `git lfs install` before cloning and verify the file is ~hundreds of MB,
  not a small pointer file.
- The database build scripts (`default_materials/`, `cell_references/`,
  `cell_teardowns/`) are Jupyter-style `# %%` scripts that drop and recreate
  tables in `database.db`. Do not run them casually.
- The build scripts require `steer-opencell-design` and `steer-materials`
  (see the `build` extra in `pyproject.toml`).
- Teardown metadata (`METADATA` / `SLUG` in each `cell_teardowns/` script) is
  validated by `steer_opencell_data/teardown_metadata.py`, which mirrors
  steer-data-infrastructure `lambda/functions/utils/teardowns.py` and the
  OpenCell app's editor — change the rules in all three. After a metadata-only
  edit run `python -m steer_opencell_data.cli.sync_metadata` rather than the
  script, and commit `database.db` once per change (each LFS commit stores the
  whole ~265 MB file).
- Tests: `pip install -e ".[cli]" pytest && python -m pytest tests`.

## Code formatting
- Use `black .` to format Python code.
- Use `isort .` to sort Python imports.
