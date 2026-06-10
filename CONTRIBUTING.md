# Contributing to steer-opencell-data

Thank you for your interest in contributing to steer-opencell-data! This document provides
guidelines and instructions for contributing.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/stanford-developers/steer-opencell-data.git
   cd steer-opencell-data
   ```
3. Install in development mode (requires [Git LFS](https://git-lfs.com/) for `database.db`):
   ```bash
   git lfs install
   pip install -e .
   ```

## Development Workflow

### Code Style

This project uses:
- **Black** for code formatting (line length 88)
- **isort** for import sorting (Black-compatible profile)
- **flake8** for linting

Format your code before committing:
```bash
black . && isort .
```

### Modifying the Database

The reference database (`steer_opencell_data/database.db`) is rebuilt by the
scripts in `default_materials/`, `cell_references/`, and `cell_teardowns/`.
These scripts drop and recreate tables, so run them deliberately. New data
contributions should include source attribution (see the attribution headers
in `cell_teardowns/` scripts) and must only contain data you have the right
to redistribute.

### Making Changes

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes
3. Format your code: `black . && isort .`
4. Commit with a clear message describing the change
5. Push to your fork and open a Pull Request

## Pull Request Guidelines

- Provide a clear description of what the PR does
- Reference any related issues
- For new data, include source attribution and confirm redistribution rights
- Ensure CI passes before requesting review

## Reporting Bugs

Open an issue on GitHub with:
- A clear title and description
- Steps to reproduce the behavior
- Expected vs actual behavior
- Python version and OS

## Feature Requests

Open an issue on GitHub describing:
- The use case for the feature
- How it would benefit steer-opencell-data users
- Any proposed implementation approach

## Contributor License Agreement (CLA)

steer-opencell-data is distributed under a **dual license** (AGPL-3.0-or-later + proprietary). To ensure
all contributions can be distributed under both licenses, we require contributors to sign
a **Contributor License Agreement** before their first pull request can be merged.

### How it works

1. Submit your pull request
2. The CLA Assistant bot will comment with a link to the [CLA](CLA.md)
3. Read the CLA and post a comment in the PR stating:
   > I have read the CLA Document and I hereby sign the CLA
4. Your signature is recorded automatically — you only need to sign once

The CLA grants the maintainer a non-exclusive license to reproduce, sublicense, and
distribute your contributions under any license — including proprietary/commercial
licenses. This is necessary to allow distribution under both the open-source
(AGPL-3.0-or-later) and proprietary licenses. For full details, see [CLA.md](CLA.md).

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
By participating, you are expected to uphold this code.

## License

steer-opencell-data is dual-licensed:

- **AGPL-3.0-or-later** — for open-source use. See [LICENSE](LICENSE).
- **Commercial license** — available for use without AGPL-3.0 copyleft requirements. Contact nsiemons@stanford.edu.

By contributing, you agree to the terms of the [Contributor License Agreement](CLA.md),
which grants the maintainer the right to distribute contributions under both licenses.
