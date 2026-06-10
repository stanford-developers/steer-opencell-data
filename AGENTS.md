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

## Code formatting
- Use `black .` to format Python code.
- Use `isort .` to sort Python imports.
