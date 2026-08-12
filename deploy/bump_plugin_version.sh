#!/bin/bash
# ==========================================================================
# VeroRun — Plugin version bump (single source of truth: plugin.json)
# ==========================================================================
# Usage:
#   bash deploy/bump_plugin_version.sh <identifier> <x.y.z>
#
# Updates plugins/<id>/plugin.json version, prepends a CHANGELOG entry to
# plugins/<id>/CHANGELOG.md, and creates git tag <id>-vX.Y.Z (which triggers
# .github/workflows/plugin-release.yml to publish the plugin package).
# Idempotent: refuses same-version re-runs and duplicate tags.
# ==========================================================================
set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
OK="${GREEN}[OK]${NC}"; FAIL="${RED}[FAIL]${NC}"; WARN="${YELLOW}[WARN]${NC}"

# ── Validate input ────────────────────────────────────────────────────
IDENTIFIER="${1:-}"
NEW="${2:-}"
if [ -z "${IDENTIFIER}" ] || [ -z "${NEW}" ]; then
    echo -e "${FAIL} Usage: bash deploy/bump_plugin_version.sh <identifier> <x.y.z>"
    exit 1
fi
if ! echo "${IDENTIFIER}" | grep -qE '^[a-zA-Z0-9_]+$'; then
    echo -e "${FAIL} Invalid identifier '${IDENTIFIER}' — expected [a-zA-Z0-9_]+"
    exit 1
fi
if ! echo "${NEW}" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo -e "${FAIL} Invalid version '${NEW}' — expected format x.y.z (e.g. 1.2.0)"
    exit 1
fi

# ── Resolve plugin dir (repo root, one level above deploy/) ───────────
APP_HOME="$(cd "$(dirname "$0")/.." && pwd)"
cd "${APP_HOME}"

PLUGIN_DIR="${APP_HOME}/plugins/${IDENTIFIER}"
PLUGIN_JSON="${PLUGIN_DIR}/plugin.json"
if [ ! -f "${PLUGIN_JSON}" ]; then
    echo -e "${FAIL} plugin.json not found: ${PLUGIN_JSON}"
    exit 1
fi

# ── Read current version ──────────────────────────────────────────────
OLD="$(python3 -c "import json;print(json.load(open('${PLUGIN_JSON}'))['version'])")"
if [ "${OLD}" = "${NEW}" ]; then
    echo -e "${WARN} Version is already ${NEW} — nothing to do"
    exit 0
fi

echo -e "${OK} Bumping plugin ${IDENTIFIER} ${OLD} -> ${NEW}"

# ── 1. Update plugin.json version ─────────────────────────────────────
python3 - "$PLUGIN_JSON" "$NEW" <<'PY'
import json, sys
path, new_ver = sys.argv[1], sys.argv[2]
with open(path, encoding='utf-8') as f:
    data = json.load(f)
data['version'] = new_ver
with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write('\n')
PY
echo -e "${OK} plugin.json version -> ${NEW}"

# ── 2. Prepend CHANGELOG entry ────────────────────────────────────────
CHANGELOG="${PLUGIN_DIR}/CHANGELOG.md"
TODAY="$(date +%Y-%m-%d)"
TMP_FILE="$(mktemp)"
trap 'rm -f "${TMP_FILE}"' EXIT
{
    echo "# Changelog"
    echo
    echo "## v${NEW} — ${TODAY}"
    echo
    echo "### Changes"
    echo
    echo "- Version bump from v${OLD}"
    echo
    # Keep all existing entries (skip title line and following blank line)
    if [ -f "${CHANGELOG}" ]; then
        if head -2 "${CHANGELOG}" | grep -qE '^# ' && [ -z "$(sed -n '2p' "${CHANGELOG}" | tr -d '[:space:]')" ]; then
            tail -n +3 "${CHANGELOG}"
        else
            echo -e "${WARN} ${CHANGELOG} header format unexpected — keeping full file"
            cat "${CHANGELOG}"
        fi
    fi
} > "${TMP_FILE}"
mv "${TMP_FILE}" "${CHANGELOG}"
echo -e "${OK} CHANGELOG.md -> v${NEW} entry prepended"

# ── 3. Create git tag <id>-vX.Y.Z ─────────────────────────────────────
TAG="${IDENTIFIER}-v${NEW}"
if timeout 30 git tag -l "${TAG}" | grep -q .; then
    echo -e "${WARN} Tag ${TAG} already exists — skipping (use 'git tag -f' to move)"
else
    timeout 30 git tag "${TAG}"
    echo -e "${OK} Git tag ${TAG} created"
fi

# ── Summary ───────────────────────────────────────────────────────────
echo
echo -e "${OK} Done. Next steps:"
echo "  git add plugins/${IDENTIFIER}/plugin.json plugins/${IDENTIFIER}/CHANGELOG.md"
echo "  git commit -m \"chore(${IDENTIFIER}): bump version to ${NEW}\""
echo "  git push origin master --tags"
echo
