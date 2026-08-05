#!/bin/bash
# ==========================================================================
# VeroRun — Single-command version bump (single source of truth: VERSION)
# ==========================================================================
# Usage:
#   bash deploy/bump_version.sh <x.y.z>     # bump version to x.y.z
#
# The VERSION file is the ONLY source of truth. This script syncs the
# derived artifacts (CHANGELOG entry, git tag) from it, so you never
# have to hand-edit multiple files again.
# ==========================================================================
set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
OK="${GREEN}[OK]${NC}"; FAIL="${RED}[FAIL]${NC}"; WARN="${YELLOW}[WARN]${NC}"

# ── Validate input ────────────────────────────────────────────────────
NEW="${1:-}"
if [ -z "${NEW}" ]; then
    echo -e "${FAIL} Usage: bash deploy/bump_version.sh <x.y.z>"
    exit 1
fi
if ! echo "${NEW}" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo -e "${FAIL} Invalid version '${NEW}' — expected format x.y.z (e.g. 0.41.0)"
    exit 1
fi

# ── Resolve project root (repo root, one level above deploy/) ─────────
APP_HOME="$(cd "$(dirname "$0")/.." && pwd)"
cd "${APP_HOME}"

OLD="$(cat VERSION 2>/dev/null || echo '0.0.0')"
if [ "${OLD}" = "${NEW}" ]; then
    echo -e "${WARN} Version is already ${NEW} — nothing to do"
    exit 0
fi

echo -e "${OK} Bumping VeroRun ${OLD} -> ${NEW}"

# ── 1. Update the single source of truth ──────────────────────────────
echo "${NEW}" > VERSION
echo -e "${OK} VERSION -> ${NEW}"

# ── 2. Prepend CHANGELOG entry ────────────────────────────────────────
TODAY="$(date +%Y-%m-%d)"
TMP_FILE="$(mktemp)"
trap 'rm -f "${TMP_FILE}"' EXIT
{
    echo "# 修改记录"
    echo
    echo "## v${NEW} — ${TODAY}"
    echo
    echo "### Changes"
    echo
    echo "- Version bump from v${OLD}"
    echo
    # Keep all existing entries (skip title line and following blank line)
    if [ -f CHANGELOG.md ]; then
        tail -n +3 CHANGELOG.md
    fi
} > "${TMP_FILE}"
mv "${TMP_FILE}" CHANGELOG.md
echo -e "${OK} CHANGELOG.md -> v${NEW} entry prepended"

# ── 3. Tag for check-update detection ─────────────────────────────────
if git tag -l "v${NEW}" | grep -q .; then
    echo -e "${WARN} Tag v${NEW} already exists — moving it to current HEAD"
    git tag -f "v${NEW}"
else
    git tag "v${NEW}"
fi
echo -e "${OK} Git tag v${NEW} created"

# ── Summary ───────────────────────────────────────────────────────────
echo
echo -e "${OK} Done. Next steps:"
echo "  git add VERSION CHANGELOG.md"
echo "  git commit -m \"chore: bump version to ${NEW}\""
echo "  git push && git push origin v${NEW}"
echo
echo "  Server: cd ~/verorun && sudo bash deploy/install.sh update"
