# steer-opencell-data

Data feed for STEER OpenCell. Contains the SQLite reference database (`database.db`) and a CLI tool for migrating records to the AWS backend.

## Install

```bash
pip install -e .
```

## CLI Migration Tool

Migrate individual records from the local SQLite database to AWS (DynamoDB + S3). Useful when new materials or cells are created locally (e.g. via Jupyter) and need to be published.

### Prerequisites

```bash
# Install with CLI dependencies
pip install -e ".[cli]"

# Configure AWS credentials
aws configure
# or set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
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

| Variable | Default | Description |
| --- | --- | --- |
| `DYNAMODB_TABLE` | `example-dynamodb-table` | Target DynamoDB table |
| `S3_BUCKET` | `example-s3-bucket` | Target S3 bucket |
| `AWS_REGION` | `us-east-2` | AWS region |
