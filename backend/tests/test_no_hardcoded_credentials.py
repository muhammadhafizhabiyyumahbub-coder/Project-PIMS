import re
from pathlib import Path

def test_no_postgres_credentials_in_tracked_files():
    """
    Ensure no tracked files contain PostgreSQL connection strings with embedded passwords.
    This prevents accidental credential leaks in source control.
    """
    # Pattern: postgresql+psycopg://user:password@host:port/db
    # This matches URIs with a password component (something between : and @)
    # Excludes URLs without passwords (postgresql+psycopg://user@host)
    pattern = re.compile(r"postgresql\+psycopg://[^:]+:[^:@]+@")

    # Files/dirs to exclude
    excluded = {".venv", ".venv-test", "venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache", ".git", "uv.lock"}

    repo_root = Path(__file__).resolve().parents[1]
    violations = []

    for file_path in repo_root.rglob("*"):
        if not file_path.is_file():
            continue
        if any(excl in file_path.parts for excl in excluded):
            continue
        # Skip this test file itself
        if file_path.name == "test_no_hardcoded_credentials.py":
            continue
        if file_path.suffix in {".pyc", ".pyo", ".so", ".dll", ".exe", ".lock"}:
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for match in pattern.finditer(content):
            # Find line number
            line_no = content[:match.start()].count("\n") + 1
            # Get the matched line (masked for safety)
            line = content.splitlines()[line_no - 1] if line_no > 0 else ""
            # Mask password in report
            masked_line = re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", line.strip())
            violations.append(
                f"{file_path.relative_to(repo_root)}:{line_no}: {masked_line}"
            )

    assert not violations, (
        "Found PostgreSQL connection strings with embedded credentials in tracked files:\n"
        + "\n".join(violations)
    )