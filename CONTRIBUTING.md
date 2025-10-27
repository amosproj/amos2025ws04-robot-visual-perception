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
  echo "❌ Commit rejected: missing 'Signed-off-by' line."
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

**Node.js 20+** (for frontend)
```bash
brew install node@20
```

**Python 3.11+** (for backend)
```bash
brew install python@3.11
```

**Go 1.21+** (for WebRTC)
```bash
brew install go@1.21
```


**uv** (Python package manager)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or on mac
brew install uv
```

**golangci-lint** (Go linter)
```bash
brew install golangci-lint
```

#### Install dependencies

After installing the tools above, run:

```bash
make dev
```

This will:
- Install frontend dependencies (npm packages)
- Create Python virtual environment and install backend dependencies
- Download Go modules

#### Running Linters

```bash
make lint # Lint all components
make lint-frontend # Lint frontend only
make lint-backend # Lint backend only
make lint-go # Lint Go code only
```

Before you push your changes, run the linters above and address lint errors if any.