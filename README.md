# steer-opencell-data

Reference data for the OpenCell platform. Contains the local SQLite reference database (`database.db`), the source scripts used to build it, and a CLI tool for migrating records to an AWS backend.

This package provides the **development-mode backend** for `from_database()` in [steer-opencell-design](https://github.com/stanford-developers/steer-opencell-design) and [steer-core](https://github.com/stanford-developers/steer-core): when `OPENCELL_ENV=development` (the default), objects are loaded from the bundled SQLite database with no network calls.

## Install

The database file is stored with [Git LFS](https://git-lfs.com/), so make sure Git LFS is installed before cloning:

```bash
git lfs install
git clone https://github.com/stanford-developers/steer-opencell-data.git
cd steer-opencell-data
pip install -e .
```

Or install directly with pip (also requires Git LFS):

```bash
pip install git+https://github.com/stanford-developers/steer-opencell-data.git
```

## Usage

With the package installed, development mode works out of the box:

```python
import steer_opencell_design as ocd

cathode = ocd.CathodeMaterial.from_database("LFP")
```

The `DataManager` can also be used directly:

```python
from steer_opencell_data.DataManager import DataManager

db = DataManager()
print(db.get_table_names())
```

## Repository Layout

| Path | Contents |
| --- | --- |
| `steer_opencell_data/database.db` | SQLite reference database (Git LFS) |
| `steer_opencell_data/DataManager.py` | SQLite-backed DataManager |
| `steer_opencell_data/cli/` | AWS migration CLI |
| `default_materials/` | Scripts that build the material tables |
| `cell_references/` | Scripts that build generic reference cell designs |
| `cell_teardowns/` | Scripts that build teardown-based cell models (see attribution headers in each script) |
| `local_data/` | Source half-cell curves and material property CSVs |

## Rebuilding the Database

The database is rebuilt by running the scripts in `default_materials/`, `cell_references/`, and `cell_teardowns/`. These scripts require additional packages, available via the `build` extra plus a separate install of `steer-opencell-design` (kept out of the hard dependencies to avoid a circular requirement):

```bash
pip install -e ".[build]"
pip install steer-opencell-design
```

Each script is a Jupyter-style (`# %%`) script that drops and recreates its table, so run them deliberately — they modify `database.db` in place.

## CLI Migration Tool

Migrate individual records from the local SQLite database to an AWS backend (DynamoDB + S3). Useful when new materials or cells are created locally and need to be published to a deployed OpenCell API.

### Prerequisites

```bash
# Install with CLI dependencies
pip install -e ".[cli]"

# Configure AWS credentials
aws configure
# or set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION

# Set the migration target (required — there are no defaults)
export DYNAMODB_TABLE=my-dynamodb-table
export S3_BUCKET=my-s3-bucket
```

### Usage

**Interactive** (prompts you through each step):

```bash
python -m steer_opencell_data.cli.migrate_record
```

**Non-interactive** (for scripting):

```bash
python -m steer_opencell_data.cli.migrate_record --table cathode_materials --name LFP --yes
```

**Dry run** (preview without writing to AWS):

```bash
python -m steer_opencell_data.cli.migrate_record --dry-run
```

### Options

| Flag | Description |
| --- | --- |
| `--table TABLE` | Skip table selection prompt |
| `--name NAME` | Skip record selection prompt |
| `--yes, -y` | Skip confirmation prompt |
| `--dry-run` | Preview without writing to AWS |
| `--sqlite-path PATH` | Override database path (default: package's `database.db`) |
| `--verbose, -v` | Verbose logging |

### Environment Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `DYNAMODB_TABLE` | Yes | — | Target DynamoDB table |
| `S3_BUCKET` | Yes | — | Target S3 bucket |
| `AWS_REGION` | No | `us-east-2` | AWS region |

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. Contributions require signing a [Contributor License Agreement](CLA.md).

## License

steer-opencell-data is dual-licensed:

- **Open source** — [GNU Affero General Public License v3.0 or later](https://www.gnu.org/licenses/agpl-3.0) (AGPL-3.0-or-later)
- **Commercial** — A separate commercial license is available for use without AGPL-3.0 copyleft requirements. Contact [nsiemons@stanford.edu](mailto:nsiemons@stanford.edu) for details.

See [LICENCE.txt](LICENCE.txt) for full terms.
