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

## Code conventions

**The class rules live in `steer-core/CODE_CONVENTIONS.md`. Read that file before you write a class.**

`steer-opencell-design` is the reference implementation. The short form:

1. Write a plain class. Do not use `@dataclass`.
2. Inherit `ValidationMixin` and `DunderMixin` from `steer_core.Mixins`. Add `DataMixin`, `DateTimeMixin`,
   and `SerializerMixin` when the class needs them.
3. Take every unit conversion and every physical constant from `steer_core.Constants`.
4. Make every public attribute a property. Declare every getter, then every setter.
5. Validate in the setter, with a `ValidationMixin` method and a capitalised label.
6. Name every internal field with a leading underscore. Compute a derived value in
   `_calculate_*_properties()` and give it no setter and no validation.
7. Store SI units internally. Convert in the getter and the setter.
