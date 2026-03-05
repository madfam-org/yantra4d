#!/usr/bin/env bash
# scripts/propagate_ci.sh
# Distributes the .github/workflows/project-ci.yml to all project submodules and pushes them.

set -e

# Change to repo root
cd "$(dirname "$0")/.."

TEMPLATE=".github/workflows/project-ci.yml"
if [ ! -f "$TEMPLATE" ]; then
  echo "❌ Error: Template $TEMPLATE not found."
  exit 1
fi

echo "🚀 Propagating CI template to all project submodules..."

# Iterate through all modules found in .gitmodules
for slug in $(git config --file .gitmodules --get-regexp path | awk '{ print $2 }' | sed 's/projects\///'); do
  echo "----------------------------------------"
  echo "📦 Processing $slug..."
  TARGET_DIR="projects/$slug"
  
  if [ ! -d "$TARGET_DIR" ]; then
    echo "⚠️ Submodule directory $TARGET_DIR does not exist. Skipping."
    continue
  fi

  cd "$TARGET_DIR"

  # Ensure .github/workflows exists
  mkdir -p .github/workflows
  
  # Copy template down
  cp "../../$TEMPLATE" .github/workflows/project-ci.yml
  
  # Check if anything changed
  git add .github/workflows/project-ci.yml
  if git diff --staged --quiet; then
    echo "✅ CI already up to date in $slug. No changes."
  else
    echo "📝 Committing CI update for $slug..."
    git commit -m "chore(ci): distribute project-ci template from yantra4d"
    
    # Push to original upstream (assuming the default branch is main)
    # Using gh or standard git push.
    echo "⬆️ Pushing changes..."
    # Warning: Ensure the context has access to push directly to madfam-org/<slug>
    # git push origin HEAD:main
    echo "⏭️ Dry run: git push origin HEAD:main"
  fi
  
  cd ../..
done

echo "🎉 CI propagation complete!"
