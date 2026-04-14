# 🚀 Release Process for Cherub Suite

This document outlines the automated release process for the Cherub Suite extension.

## Automated Workflows

We have three main GitHub Actions workflows:

### 1. **Validate** (`.github/workflows/validate.yml`)
- **Trigger**: Every push to `main`/`develop` and all PRs
- **What it does**:
  - Validates `.blender_ext.toml` and `manifest.toml` syntax
  - Checks Python syntax
  - Verifies required files exist
  - Warns if deprecated files still have active code

### 2. **Build** (`.github/workflows/build.yml`)
- **Trigger**: Every push to `main`/`develop` and all PRs
- **What it does**:
  - Creates a `.zip` package of the extension
  - Verifies all required files are in the package
  - Uploads artifact for download (retained 30 days)
  - Comments on PRs with download link

### 3. **Release** (`.github/workflows/release.yml`)
- **Trigger**: When a tag is pushed (e.g., `v0.2.0`)
- **What it does**:
  - Validates tag version matches `.blender_ext.toml`
  - Creates extension package
  - Creates a GitHub release with pre-formatted notes
  - Uploads the `.zip` to the release

### 4. **Bump Version** (`.github/workflows/bump-version.yml`)
- **Trigger**: Manual workflow dispatch
- **What it does**:
  - Bumps version in all manifest files
  - Creates a pull request for review
  - Supports major/minor/patch bumps

## Step-by-Step Release Guide

### Option A: Full Automated Release (Recommended)

1. **Bump Version**
   ```bash
   # Go to Actions → Bump Version → Run workflow
   # Select version type: patch, minor, or major
   # Review and merge the created PR
   ```

2. **Create Release Tag**
   ```bash
   git pull origin main
   git tag v0.2.1
   git push origin v0.2.1
   ```

3. **Done!** 🎉
   - The "Release" workflow automatically:
     - Creates a GitHub release
     - Packages the extension
     - Uploads the `.zip` file
     - Generates release notes

### Option B: Manual Version Bump + Release

1. **Update Version Manually**
   - Edit `.blender_ext.toml` and update `version`
   - Edit `manifest.toml` and update `version`
   - Edit `__init__.py` and update `bl_info["version"]`
   
2. **Commit & Push**
   ```bash
   git add .blender_ext.toml manifest.toml __init__.py
   git commit -m "chore: bump version to 0.2.1"
   git push origin main
   ```

3. **Create Tag**
   ```bash
   git tag v0.2.1
   git push origin v0.2.1
   ```

## Version Numbering

We use **Semantic Versioning**: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (rare for extensions)
- **MINOR**: New features (proportional editing variants, new pie menus, etc.)
- **PATCH**: Bug fixes, small improvements

Example progression:
- `0.1.0` → `0.2.0` (minor: new features)
- `0.2.0` → `0.2.1` (patch: bug fix)
- `0.2.1` → `1.0.0` (major: breaking changes)

## Testing Before Release

Before creating a release tag, verify:

1. **Addon loads in Blender 5.1+**
   - Enable in Edit → Preferences → Extensions
   - Check console for errors

2. **Pie menus work**
   - Test hotkeys (X, W, Q, O, etc.)
   - Verify operators execute

3. **Manifests are valid**
   - The Validate workflow should pass (green checkmark)

## Troubleshooting

### Tag version doesn't match manifest version
```
ERROR: Tag version (0.2.1) does not match .blender_ext.toml version (0.2.0)
```
**Solution**: Update `.blender_ext.toml` and `manifest.toml` with the correct version before tagging.

### Release workflow failed
- Check the Actions tab for the specific error
- Most common: version mismatch (see above)
- Fix the issue, delete the tag, and retry:
  ```bash
  git tag -d v0.2.1
  git push origin :v0.2.1
  ```

### I need to rollback a release
1. Delete the release on GitHub
2. Delete the tag: `git tag -d v0.2.1 && git push origin :v0.2.1`
3. Revert commits if needed
4. Create a new release when ready

## Tips

- ✅ Always test locally in Blender before releasing
- ✅ Use descriptive commit messages
- ✅ Let GitHub Actions validate your changes
- ✅ Review generated release notes
- ✅ Keep CHANGELOG.md updated with user-facing changes
- ❌ Don't manually edit `__init__.py`, `manifest.toml`, or `.blender_ext.toml` version after tagging
