# Contributing Guidelines

Thank you for your interest in contributing to this project. To ensure the codebase remains consistent, high-quality, and easy to maintain, we ask that you adhere to the following guidelines.

## 1. Project Setup with `uv`

We use **`uv`** for managing the virtual environment and project dependencies. It is an extremely fast, all-in-one tool that replaces `pip` and `venv`.

### Step 1: Install `uv`

If you don't have `uv` installed, you can install it with:
```bash
# On macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Step 2: Create and Activate the Virtual Environment

1.  **Create the environment:** This command creates a virtual environment in a `.venv` directory in your project's root.
    ```bash
    uv venv
    ```

2.  **Activate the environment:**
    ```bash
    # On macOS and Linux
source .venv/bin/activate

    # On Windows
    .venv\Scripts\activate
    ```

### Step 3: Install Dependencies

Once the environment is activated, install the required packages from `requirements.txt`:
```bash
uv pip install -r requirements.txt
```

## 2. Development Workflow

-   **Branching:** Create a new branch for each feature or bug fix (`git checkout -b feature/my-feature`).
-   **Commit Messages:** Follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification (e.g., `feat: ...`, `fix: ...`).

## 3. Code Quality and Tooling

We enforce strict quality standards using the following tools. All checks must pass before merging code.

### Linting and Formatting with Ruff

-   **Check for errors:**
    ```bash
    ruff check .
    ```
-   **Format and auto-fix errors:**
    ```bash
    ruff format . && ruff check . --fix
    ```

### Static Type Checking with MyPy

-   **Run type checking:**
    ```bash
    mypy src/
    ```

### Testing with Pytest

-   **Run all tests:**
    ```bash
    pytest
    ```

## 4. Automation with Pre-commit Hooks

We use **pre-commit hooks** to automatically run the quality checks before each commit.

### Setup

1.  **Install pre-commit:**
    ```bash
    uv pip install pre-commit
    ```

2.  **Create the configuration file (`.pre-commit-config.yaml`):**
    ```yaml
    repos:
    -   repo: https://github.com/pre-commit/pre-commit-hooks
        rev: v4.6.0
        hooks:
        -   id: trailing-whitespace
        -   id: end-of-file-fixer
        -   id: check-yaml
        -   id: check-added-large-files

    -   repo: https://github.com/astral-sh/ruff-pre-commit
        rev: v0.5.5
        hooks:
        -   id: ruff
            args: [--fix]
        -   id: ruff-format

    -   repo: https://github.com/pre-commit/mirrors-mypy
        rev: v1.11.0
        hooks:
        -   id: mypy
            args: [--strict]
    ```

3.  **Install the hooks into your git repo:**
    ```bash
    pre-commit install
    ```

## 5. Dependency Management

All project dependencies must be listed in `requirements.txt`. If you add or update a dependency, regenerate the file using `uv`:

```bash
uv pip freeze > requirements.txt
```
