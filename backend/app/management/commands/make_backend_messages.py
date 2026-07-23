"""
Management command to scan backend source code for user-facing strings
that should be wrapped in _() (gettext) for internationalization.

This is a SKAFFOLD / INVENTORY command — it does NOT modify any files.
It simply reports candidate strings that are hardcoded in Czech and likely
need i18n treatment. Full implementation would require careful per-string
evaluation and is beyond the scope of this initial pass.

Usage:
    python manage.py make_backend_messages [--app practices] [--write]
"""

import ast
import os
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

# Patterns that suggest a user-facing Czech string
CZECH_PATTERNS = [
    re.compile(r"^[A-ZÁČĎÉĚÍŇÓŘŠŤŮÚÝŽ].*[a-záčďéěíňóřšťůúýž]", re.UNICODE),
    re.compile(r"^[a-záčďéěíňóřšťůúýž]", re.UNICODE),
]

# Known false positives — strings that are NOT user-facing but match patterns
SKIP_PATTERNS = [
    re.compile(r"^(base_dir|settings|logger|os\.environ)", re.IGNORECASE),
    re.compile(r"^[a-f0-9]{32,}$"),  # hex hashes
    re.compile(r"^\d{4}-\d{2}-\d{2}"),  # ISO dates
]

# File extensions to scan
SCAN_EXTENSIONS = {".py"}

# Directories to exclude
EXCLUDE_DIRS = {
    "__pycache__",
    "migrations",
    ".pytest_cache",
    "venv",
    ".venv",
    "env",
    ".env",
}


def _should_skip(line: str) -> bool:
    """Return True if the line should be skipped (not user-facing)."""
    for pat in SKIP_PATTERNS:
        if pat.search(line):
            return True
    return False


def _is_czech_candidate(text: str) -> bool:
    """Rough heuristic: contains Czech-specific characters or common Czech words."""
    czech_chars = set("áčďéěíňóřšťůúýžÁČĎÉĚÍŇÓŘŠŤŮÚÝŽ")
    if any(c in text for c in czech_chars):
        return True
    # Common Czech words that likely appear in user-facing strings
    czech_words = ["prosím", "děkujeme", "chyba", "nebyl", "byla", "bylo", "zadejte", "vyberte"]
    lower = text.lower()
    return any(w in lower for w in czech_words)


class Command(BaseCommand):
    help = "Scan backend source for user-facing strings that should use gettext _()."

    def add_arguments(self, parser):
        parser.add_argument(
            "--app",
            type=str,
            default="",
            help="Only scan a specific app directory (e.g., 'practices', 'users').",
        )
        parser.add_argument(
            "--write",
            action="store_true",
            help="If set, write a report file instead of printing to stdout.",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="i18n_candidates.txt",
            help="Output file path (used with --write).",
        )

    def handle(self, *args, **options):
        base_dir = Path(options.get("app", "") or str(Path(__file__).resolve().parent.parent.parent.parent))
        target_app = options.get("app", "")

        backend_dir = base_dir
        # If an app name is given, find it under backend/
        if target_app:
            backend_dir = Path(__file__).resolve().parent.parent.parent.parent / target_app
            if not backend_dir.is_dir():
                raise CommandError(f"App directory not found: {backend_dir}")

        candidates = []

        for root, dirs, files in os.walk(backend_dir):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in SCAN_EXTENSIONS:
                    continue
                fpath = os.path.join(root, fname)
                self._scan_file(fpath, candidates)

        if not candidates:
            self.stdout.write(self.style.SUCCESS("No i18n candidate strings found."))
            return

        if options.get("write"):
            output_path = Path(options["output"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("# InternHub i18n candidate strings\n")
                f.write("# Review each candidate and wrap in _() if user-facing.\n\n")
                for fpath, line_no, line in candidates:
                    f.write(f"{fpath}:{line_no}: {line.strip()}\n")
            self.stdout.write(self.style.SUCCESS(f"Report written to {output_path}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Found {len(candidates)} i18n candidate(s):\n"))
            for fpath, line_no, line in candidates[:30]:
                self.stdout.write(f"  {fpath}:{line_no}: {line.strip()}")
            if len(candidates) > 30:
                self.stdout.write(f"  ... and {len(candidates) - 30} more (use --write to save full report).")

    def _scan_file(self, fpath: str, candidates: list):
        """Scan a single .py file for hardcoded Czech strings in string literals."""
        try:
            with open(fpath, encoding="utf-8") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return

        try:
            tree = ast.parse(content, filename=fpath)
        except SyntaxError:
            return

        for node in ast.walk(tree):
            # Look for string literals
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                text = node.value.strip()
                if len(text) < 10:
                    continue
                if _should_skip(text):
                    continue
                # Check if this is a Czech candidate string (heuristic)
                if _is_czech_candidate(text) and not self._is_already_wrapped(content, node):
                    candidates.append((fpath, node.lineno, text[:120]))

    def _is_already_wrapped(self, content: str, node: ast.Constant) -> bool:
        """Check if the string is already wrapped in _() or gettext()."""
        line = content.splitlines()[node.lineno - 1] if node.lineno else ""
        stripped = line.strip()
        # Check for _("...") or gettext("...") patterns before the string
        idx = stripped.find(node.value[:20]) if len(node.value) > 20 else -1
        if idx <= 0:
            idx = max(0, len(stripped) - len(node.value) - 2)
        before = stripped[:idx].strip()
        return before.endswith("_(") or before.endswith("gettext(") or before.endswith("ngettext(")
