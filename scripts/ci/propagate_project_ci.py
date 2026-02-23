#!/usr/bin/env python3
"""
Propagate CI Workflow Script
Iterates through all 33 Yantra4D projects and pushes a standard `ci.yml` file to each.

Requires GitHub CLI (gh) authenticated with sufficient permissions.
"""

import os
import subprocess
import sys
from pathlib import Path

PROJECTS_DIR = Path(__file__).parent.parent.parent / "projects"

CI_WORKFLOW_CONTENT = """name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    uses: madfam-org/yantra4d/.github/workflows/project-ci-reusable.yml@main
    secrets:
      DISPATCH_TOKEN: ${{ secrets.DISPATCH_TOKEN }}
"""

def main():
    if not PROJECTS_DIR.exists():
        print(f"Error: Could not find projects directory at {PROJECTS_DIR}")
        sys.exit(1)

    print(f"Propagating CI template to projects in {PROJECTS_DIR}")
    
    # Check if gh CLI is available
    if subprocess.run(["gh", "--version"], capture_output=True).returncode != 0:
        print("Error: GitHub CLI (gh) is not installed or not working.")
        sys.exit(1)

    successful = 0
    failed = []

    for project_dir in sorted(PROJECTS_DIR.iterdir()):
        if not project_dir.is_dir() or not (project_dir / "project.json").exists():
            continue
            
        slug = project_dir.name
        repo_name = f"madfam-org/{slug}"
        print(f"\nProcessing {slug} ({repo_name})...")

        # Create a temporary file containing the workflow
        tmp_file = f"/tmp/ci_{slug}.yml"
        with open(tmp_file, "w", encoding="utf-8") as f:
            f.write(CI_WORKFLOW_CONTENT)
            
        try:
            # Check if file already exists in remote
            check_cmd = ["gh", "api", f"repos/{repo_name}/contents/.github/workflows/ci.yml", "--silent"]
            file_exists = subprocess.run(check_cmd, capture_output=True).returncode == 0
            
            commit_msg = "chore(ci): Add reusable CI workflow for automated compliance and verification"
            
            # Note: We don't have direct path push via GH API reliably across platforms, but we can use git or gh api PUT
            # Base64 encoding for the GitHub API PUT
            import base64
            b64_content = base64.b64encode(CI_WORKFLOW_CONTENT.encode("utf-8")).decode("utf-8")
            
            # If the file exists, we need its SHA
            sha = ""
            if file_exists:
                sha_cmd = subprocess.run(["gh", "api", f"repos/{repo_name}/contents/.github/workflows/ci.yml", "--jq", ".sha"], capture_output=True, text=True)
                if sha_cmd.returncode == 0:
                    sha = sha_cmd.stdout.strip()
            
            payload = {
                "message": commit_msg,
                "content": b64_content,
                "branch": "main"
            }
            if sha:
                payload["sha"] = sha
                
            import json
            payload_str = json.dumps(payload)
            
            put_cmd = ["gh", "api", "-X", "PUT", f"repos/{repo_name}/contents/.github/workflows/ci.yml", "--input", "-"]
            
            process = subprocess.run(put_cmd, input=payload_str, text=True, capture_output=True)
            if process.returncode == 0:
                print(f"✅ Successfully committed CI workflow to {repo_name}")
                successful += 1
            else:
                print(f"❌ Failed to commit to {repo_name}:")
                print(process.stderr)
                failed.append(slug)
                
        except Exception as e:
            print(f"❌ Exception processing {slug}: {e}")
            failed.append(slug)
            
        finally:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)
                
    print("\n" + "="*50)
    print(f"Propagation complete: {successful} successful, {len(failed)} failed.")
    if failed:
        print(f"Failed projects: {', '.join(failed)}")

if __name__ == "__main__":
    main()
