<!--
SPDX-FileCopyrightText: 2025 robot-visual-perception

SPDX-License-Identifier: CC-BY-4.0
-->

# Contributing 101

## Quick start

### 1. Clone the repo

```bash
git clone https://github.com/amosproj/amos2025ws04-robot-visual-perception.git
cd amos2025ws04-robot-visual-perception
```

If you already cloned it earlier, update before starting work:

```bash
git pull
```

### 2. Create new branch

```bash
git checkout -b feat/<issue-number>-<short-description>
```
Let's try to follow the convention below:
- `feat` for new features
- `docs` for docs
- `fix` for bugfixes
- `exp` for anything experimental

E.g., `feat/14-architecture`

### 3. Make changes and commit

```bash
git add .
git commit  --signoff -m "A good description of the commit"
```
All commits must be signed off as per AMOS requirements. You can make Git reject unsigned commits automatically:

```bash
cd .git/hooks
nano commit-msg
```

Paste the following:
```bash
#!/bin/sh
if ! grep -q '^Signed-off-by:' "$1"; then
  echo "Commit rejected: missing 'Signed-off-by' line."
  echo "Please use: git commit -s"
  exit 1
fi
```

Then make it executable:
```bash
chmod +x .git/hooks/commit-msg
```


If several people contributed, add co-authors:

```
git commit -a -m "Fixed problem
> Co-authored-by: Stefan Buchner <stefan.buchner@fau.de>”
> --signoff
```

### 4. Push your branch
```
git push feat/<issue-number>-<short-description>
```

### 5. Open a PR

- Open a PR from your branch into `main`
- Assign yourself
- Link the related issue
- Add a good PR description 
- Ensure CI passes


### 6. Closing a PR

- Never delete branches

## Development setup

Before you can run the project locally, install the required tools:

#### Prerequisites

**Node.js 20** (for frontend)

Recommended: Use [nvm](https://github.com/nvm-sh/nvm) to manage Node.js versions:
```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

cd src/frontend
nvm install  # Installs Node.js 20
nvm use      # Switches to Node.js 20
```

Alternative (without nvm):
```bash
brew install node@20
```

**Python 3.11** (for backend)

The Makefile will automatically install Python 3.11 via `uv`. You just need `uv` installed:

**uv** (Python package manager)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or on macOS
brew install uv
```

**Docker** (for containerization)
```bash
brew install --cask docker
```

### Quick Start for Windows

For Windows developers, use our automated setup script that handles all prerequisites:
```powershell
PowerShell -ExecutionPolicy Bypass -File .\start-optibot.ps1
```

**What it does:**
- Checks for administrator privileges
- Installs Chocolatey (if not present)
- Installs Git, Python 3.11, Node.js 20+, Make, and uv
- Runs `make dev` to install dependencies
- Starts webcam, analyzer, and frontend services in separate windows
- Opens browser to http://localhost:3000

**Optional parameters:**
```powershell
# Custom camera settings
.\start-optibot.ps1 -CameraIndex 1 -CameraWidth 1920 -CameraHeight 1080 -CameraFPS 60

# Skip the build step (if already built)
.\start-optibot.ps1 -SkipBuild

# Custom backend port
.\start-optibot.ps1 -BackendPort 8080
```

**Note:** Administrator rights are required for installing dependencies via Chocolatey.

For manual setup or non-Windows platforms, follow the instructions below.

## Development

#### Install dependencies

After installing the tools above, run:

```bash
make dev
```

This will:
- Install frontend dependencies (npm packages)
- Create Python virtual environment and install backend dependencies

#### Formatting

Format your code before committing to maintain consistent style:

```bash
make format                # Format all code (frontend and backend)
make format-frontend       # Format frontend with Prettier
make format-backend        # Format backend with Ruff
```

#### Running linters

Linting catches code issues and enforces style guidelines. Always run before pushing:

```bash
make lint                  # Lint all components (includes type checking)
make lint-frontend         # Lint frontend with ESLint
make lint-backend          # Lints and type checks backend with Ruff
```

Before you push your changes, run `make lint` and address any errors.

#### Running tests

```bash
make test                  # Run all tests (frontend and backend)
make test-frontend         # Run frontend tests with Vitest
make test-backend          # Run backend tests with pytest
```

#### Docker commands

Build and run Docker containers locally:

```bash
make docker-build          # Build all Docker images
make docker-build-frontend # Build frontend image
make docker-build-backend  # Build backend image

make docker-run-frontend   # Run frontend container (opens browser)
make docker-run-backend    # Run backend container (also opens browser)

make docker-stop           # Stop all running containers
make docker-clean          # Stop containers and remove images
```
