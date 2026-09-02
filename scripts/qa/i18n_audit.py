#!/usr/bin/env python3
"""Audit i18n completeness across studio locale files and component usage.

Checks:
1. All locale files have the same set of keys (no missing translations).
   This is a HARD GATE: a missing key ships an untranslated UI, so it fails.
2. Scans studio JSX/TSX components for hardcoded English string literals not
   wrapped in t(). This is a RATCHET, not a gate: the count is compared with
   the baseline in i18n_baseline.json and only a RISE fails. The existing
   backlog does not block unrelated work; adding to it does.

Run:
    python3 scripts/qa/i18n_audit.py
    python3 scripts/qa/i18n_audit.py --update-baseline   # after fixing strings

Exit code 0 = all clear, 1 = issues found.
"""
import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOCALES_DIR = REPO_ROOT / "apps" / "studio" / "src" / "locales"
COMPONENTS_DIR = REPO_ROOT / "apps" / "studio" / "src" / "components"
BASELINE_PATH = Path(__file__).resolve().parent / "i18n_baseline.json"

# Strings that are allowed to appear hardcoded (not i18n candidates).
# Matched case-INSENSITIVELY, so keep these to tokens no user ever reads.
ALLOWED_HARDCODED = {
    "px", "rem", "em", "%", "auto", "none", "flex", "grid", "block",
    "hidden", "absolute", "relative", "fixed", "sticky",
    "GET", "POST", "PUT", "DELETE", "PATCH",
    "utf-8", "application/json", "content-type",
    "div", "span", "button", "input", "select", "option",
    "true", "false", "null", "undefined",
}

# False positives of the regex below, matched case-SENSITIVELY because these
# are exact identifiers from web APIs, not prose. They are capitalised English
# words in quotes, which is precisely the shape the audit hunts for, but they
# are compared against `KeyboardEvent.key` / `DOMException.name` — translating
# any of them would break the app rather than localise it.
#
# Case-sensitive so a genuinely user-visible label that happens to collide
# ("Enter your project name") is not waived: the regex captures the WHOLE
# quoted string, so only an exact match is skipped.
ALLOWED_WEB_API_IDENTIFIERS = {
    # KeyboardEvent.key values — e.g. `if (e.key === 'Escape') onClose()`
    "Escape", "Enter", "Tab", "Backspace", "Delete", "Home", "End",
    "PageUp", "PageDown", "Space",
    "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight",
    # DOMException / Error names — e.g. `err.name === 'AbortError'`
    "AbortError", "NotAllowedError", "NotFoundError", "NotSupportedError",
    "QuotaExceededError", "SecurityError", "TypeError",
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


def scan_hardcoded_strings():
    """Scan JSX/TSX components for potential hardcoded English strings.

    Returns a sorted list of "path:line — text" findings.
    """
    if not COMPONENTS_DIR.exists():
        print(f"WARNING: Components directory not found: {COMPONENTS_DIR}")
        return []

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
                    if text in ALLOWED_WEB_API_IDENTIFIERS:
                        continue
                    if len(text) < 4:
                        continue
                    issues.append(f"  {filepath.relative_to(REPO_ROOT)}:{i} — \"{text}\"")

    return sorted(issues)


def read_baseline():
    """Current allowed hardcoded-string count. Missing file = ratchet at zero."""
    try:
        with open(BASELINE_PATH, "r", encoding="utf-8") as f:
            return int(json.load(f)["hardcoded_strings"])
    except FileNotFoundError:
        print(f"WARNING: No baseline at {BASELINE_PATH}; ratcheting against 0")
        return 0
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        print(f"ERROR: Malformed baseline at {BASELINE_PATH}: {e}")
        return None


def write_baseline(count):
    with open(BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump({"hardcoded_strings": count}, f, indent=2)
        f.write("\n")


def check_hardcoded_strings(update_baseline=False):
    """Ratchet the hardcoded-string count against its stored baseline."""
    issues = scan_hardcoded_strings()
    count = len(issues)
    baseline = read_baseline()
    if baseline is None:
        return False

    if update_baseline:
        write_baseline(count)
        print(f"HARDCODED STRINGS: baseline updated {baseline} -> {count}")
        return True

    # Always print the findings: a ratchet nobody can read is a number, not a
    # gate. Capped so a regression does not bury the summary.
    if issues:
        print(f"HARDCODED STRINGS: {count} found (baseline {baseline})")
        for issue in issues[:50]:
            print(issue)
        if count > 50:
            print(f"  ... and {count - 50} more")
    else:
        print(f"HARDCODED STRINGS: 0 found (baseline {baseline})")

    if count > baseline:
        print()
        print(
            f"ERROR: hardcoded strings rose {baseline} -> {count}. Wrap the new "
            f"string(s) in t(), or — if the match is a web-API identifier such "
            f"as a KeyboardEvent.key value — add it to "
            f"ALLOWED_WEB_API_IDENTIFIERS in this script with a comment."
        )
        return False

    if count < baseline:
        print()
        print(
            f"Hardcoded strings fell {baseline} -> {count}. Lower the ratchet: "
            f"python3 scripts/qa/i18n_audit.py --update-baseline"
        )
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Rewrite i18n_baseline.json to the current hardcoded-string count.",
    )
    args = parser.parse_args(argv)

    print("=" * 60)
    print("Yantra4D i18n Audit")
    print("=" * 60)
    print()

    parity_ok = check_locale_key_parity()
    print()
    hardcoded_ok = check_hardcoded_strings(update_baseline=args.update_baseline)
    print()

    if parity_ok and hardcoded_ok:
        print("RESULT: All i18n checks passed.")
        return 0
    else:
        print("RESULT: Issues found. See above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
