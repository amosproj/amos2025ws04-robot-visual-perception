# Contributing 101

### 1. Clone the repo

```
git clone https://github.com/amosproj/amos2025ws04-robot-visual-perception.git
cd amos2025ws04-robot-visual-perception
```

If you already cloned it earlier, update before starting work:

```
git pull
```

### 2. Create new branch

```
git checkout -b feat/<issue-number>-<short-description>
```
Let's try to follow the convention below:
- `feat` for new features
- `docs` for docs
- `fix` for bugfixes
- `exp` for anything experimental

E.g., `feat/14-architecture`

### 3. Make changes and commit

```
git add .
git commit  --signoff -m "A good description of the commit"
```
> All commits must be signed off

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