#!/usr/bin/env python3
"""Audit i18n completeness across studio locale files and component usage.

Checks:
1. All locale files have the same set of keys (no missing translations).
2. Scans studio JSX components for hardcoded English string literals not wrapped in t().

Exit code 0 = all clear, 1 = issues found.
"""
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOCALES_DIR = REPO_ROOT / "apps" / "studio" / "src" / "locales"
COMPONENTS_DIR = REPO_ROOT / "apps" / "studio" / "src" / "components"

# Strings that are allowed to appear hardcoded (not i18n candidates)
ALLOWED_HARDCODED = {
    "px", "rem", "em", "%", "auto", "none", "flex", "grid", "block",
    "hidden", "absolute", "relative", "fixed", "sticky",
    "GET", "POST", "PUT", "DELETE", "PATCH",
    "utf-8", "application/json", "content-type",
    "div", "span", "button", "input", "select", "option",
    "true", "false", "null", "undefined",
}

# Regex to match JSX string literals that might be user-visible text
# Matches: "Some text" or 'Some text' in JSX attribute values or children
HARDCODED_PATTERN = re.compile(
    r"""(?:>|=\s*)["']([A-Z][a-zA-Z\s]{3,})["']"""
)


def flatten_keys(obj, prefix=""):
    """Recursively flatten a nested dict into dot-separated keys."""
    keys = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_key = f"{prefix}.{k}" if prefix else k
            keys.update(flatten_keys(v, new_key))
    else:
        keys.add(prefix)
    return keys


def check_locale_key_parity():
    """Compare keys across all locale files; report missing keys."""
    locale_files = sorted(LOCALES_DIR.glob("*.json"))
    if not locale_files:
        print(f"ERROR: No locale files found in {LOCALES_DIR}")
        return False

    locale_keys = {}
    for lf in locale_files:
        lang = lf.stem
        with open(lf, "r", encoding="utf-8") as f:
            data = json.load(f)
        locale_keys[lang] = flatten_keys(data)

    all_keys = set()
    for keys in locale_keys.values():
        all_keys.update(keys)

    issues = []
    for lang, keys in sorted(locale_keys.items()):
        missing = all_keys - keys
        if missing:
            for key in sorted(missing):
                issues.append(f"  [{lang}] missing key: {key}")

    if issues:
        print(f"LOCALE KEY PARITY: {len(issues)} missing keys across {len(locale_keys)} locales")
        for issue in issues:
            print(issue)
        return False

    print(f"LOCALE KEY PARITY: OK ({len(all_keys)} keys across {len(locale_keys)} locales)")
    return True


def check_hardcoded_strings():
    """Scan JSX/TSX components for potential hardcoded English strings."""
    if not COMPONENTS_DIR.exists():
        print(f"WARNING: Components directory not found: {COMPONENTS_DIR}")
        return True

    issues = []
    for ext in ("*.jsx", "*.tsx"):
        for filepath in COMPONENTS_DIR.rglob(ext):
            # Skip test files and Shadcn UI primitives
            if ".test." in filepath.name or "/ui/" in str(filepath):
                continue

            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                # Skip comments, imports, and lines using t()
                stripped = line.strip()
                if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("import"):
                    continue
                if "t(" in line or "t('" in line or 't("' in line:
                    continue

                matches = HARDCODED_PATTERN.findall(line)
                for match in matches:
                    text = match.strip()
                    if text.lower() in ALLOWED_HARDCODED:
                        continue
                    if len(text) < 4:
                        continue
                    issues.append(f"  {filepath.relative_to(REPO_ROOT)}:{i} — \"{text}\"")

    if issues:
        print(f"HARDCODED STRINGS: {len(issues)} potential untranslated strings found")
        for issue in issues[:50]:  # Cap output
            print(issue)
        if len(issues) > 50:
            print(f"  ... and {len(issues) - 50} more")
        return False

    print("HARDCODED STRINGS: OK (no obvious untranslated strings)")
    return True


def main():
    print("=" * 60)
    print("Yantra4D i18n Audit")
    print("=" * 60)
    print()

    parity_ok = check_locale_key_parity()
    print()
    hardcoded_ok = check_hardcoded_strings()
    print()

    if parity_ok and hardcoded_ok:
        print("RESULT: All i18n checks passed.")
        return 0
    else:
        print("RESULT: Issues found. See above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
