#!/usr/bin/env python3
"""
Plugin Publisher
================
Publishes a plugin from verorun-code to the verorun-store GitHub Releases.

Usage:
    python tools/publish_plugin.py <plugin_identifier> [--version X.Y.Z]

Environment:
    GITHUB_TOKEN  - GitHub Personal Access Token (repo scope required)
    GITHUB_REPO   - Target repo (default: fanjumin/verorun-store)
    GITHUB_BRANCH - Target branch (default: main)

Examples:
    python tools/publish_plugin.py analytics
    python tools/publish_plugin.py sms --version 0.6.0
"""

import os
import sys
import json
import hashlib
import zipfile
import tempfile
import shutil
import base64
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


# ── Configuration ──────────────────────────────────────────────────────

REPO = os.environ.get('GITHUB_REPO', 'fanjumin/verorun-store')
BRANCH = os.environ.get('GITHUB_BRANCH', 'main')
TOKEN = os.environ.get('GITHUB_TOKEN', '')
API_BASE = f'https://api.github.com/repos/{REPO}'
RAW_BASE = f'https://raw.githubusercontent.com/{REPO}/{BRANCH}'
PLUGINS_DIR = Path(__file__).resolve().parent.parent / 'plugins'


# ── Helpers ────────────────────────────────────────────────────────────

def _api_request(method: str, path: str, data: dict = None,
                 content_type: str = 'application/json') -> dict:
    """Call GitHub API v3."""
    url = f'{API_BASE}{path}'
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'User-Agent': 'VeroRun-Publisher/1.0',
        'Accept': 'application/vnd.github+json',
    }
    body = None
    if data is not None:
        if content_type == 'application/json':
            body = json.dumps(data).encode()
            headers['Content-Type'] = 'application/json'
        else:
            body = data if isinstance(data, bytes) else data.encode()
            headers['Content-Type'] = content_type

    req = Request(url, data=body, method=method, headers=headers)
    try:
        with urlopen(req, timeout=60) as resp:
            content = resp.read()
            if not content:
                return {}
            return json.loads(content.decode())
    except HTTPError as e:
        err_body = e.read().decode() if e.fp else ''
        raise RuntimeError(f'GitHub API error {e.code}: {err_body}')
    except URLError as e:
        raise RuntimeError(f'Network error: {e}')


def _sha256_file(filepath: str) -> str:
    """Compute SHA256 hex digest of a file."""
    sha = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            sha.update(chunk)
    return sha.hexdigest()


def _zip_plugin(identifier: str, plugin_dir: Path) -> tuple:
    """Create a zip archive of the plugin directory.

    Returns:
        (zip_path, file_size)
    """
    tmp_dir = tempfile.mkdtemp(prefix=f'vrplug_{identifier}_')
    zip_name = f'{identifier}-v{PLUGIN_VERSION}.zip'
    zip_path = os.path.join(tmp_dir, zip_name)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(plugin_dir):
            # Skip __pycache__ and .git
            dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git', '.gitignore')]
            for fname in files:
                if fname.endswith('.pyc'):
                    continue
                full_path = os.path.join(root, fname)
                arcname = os.path.relpath(full_path, plugin_dir)
                zf.write(full_path, arcname)

    file_size = os.path.getsize(zip_path)
    return zip_path, file_size


# ── GitHub Release ─────────────────────────────────────────────────────

def _create_release(tag: str, name: str, body: str) -> dict:
    """Create a GitHub Release (creates the tag if it doesn't exist)."""
    print(f'  Creating release: {tag}')
    return _api_request('POST', '/releases', {
        'tag_name': tag,
        'name': name,
        'body': body,
        'draft': False,
        'prerelease': False,
    })


def _upload_asset(release_id: int, filepath: str, filename: str):
    """Upload a file as a release asset."""
    print(f'  Uploading asset: {filename}')
    with open(filepath, 'rb') as f:
        content = f.read()
    url = f'{API_BASE}/releases/{release_id}/assets?name={filename}'
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'User-Agent': 'VeroRun-Publisher/1.0',
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/zip',
    }
    req = Request(url, data=content, method='POST', headers=headers)
    try:
        with urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        err_body = e.read().decode() if e.fp else ''
        raise RuntimeError(f'Upload failed ({e.code}): {err_body}')


# ── Catalog Update ─────────────────────────────────────────────────────

def _get_catalog() -> tuple:
    """Fetch current store_catalog.json from GitHub.

    Returns:
        (catalog_dict, file_sha)
    """
    print('  Fetching current store_catalog.json...')
    resp = _api_request('GET', f'/contents/store_catalog.json?ref={BRANCH}')
    content_b64 = resp.get('content', '')
    sha = resp.get('sha', '')
    if content_b64:
        catalog = json.loads(base64.b64decode(content_b64).decode())
    else:
        catalog = {'version': '1.0', 'updated_at': '', 'plugins': []}
    return catalog, sha


def _update_catalog(catalog: dict, sha: str, plugin_entry: dict,
                    identifier: str):
    """Update or add plugin entry in catalog, then commit."""
    plugins = catalog.get('plugins', [])
    found = False
    for i, p in enumerate(plugins):
        if p.get('identifier') == identifier:
            plugins[i] = plugin_entry
            found = True
            break
    if not found:
        plugins.append(plugin_entry)

    catalog['plugins'] = plugins
    catalog['updated_at'] = __import__('datetime').datetime.now().isoformat()

    content = json.dumps(catalog, indent=2, ensure_ascii=False)
    content_b64 = base64.b64encode(content.encode()).decode()

    print(f'  Updating store_catalog.json ({len(plugins)} plugins)...')
    _api_request('PUT', f'/contents/store_catalog.json', {
        'message': f'Publish {identifier} v{PLUGIN_VERSION}',
        'content': content_b64,
        'sha': sha,
        'branch': BRANCH,
    })
    print(f'  Catalog updated.')


# ── Main ───────────────────────────────────────────────────────────────

def main():
    global PLUGIN_VERSION

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    identifier = sys.argv[1]
    plugin_dir = PLUGINS_DIR / identifier

    if not plugin_dir.is_dir():
        print(f'Error: Plugin "{identifier}" not found at {plugin_dir}')
        sys.exit(1)

    # Parse --version
    version_override = None
    args = sys.argv[2:]
    for i, arg in enumerate(args):
        if arg == '--version' and i + 1 < len(args):
            version_override = args[i + 1]

    # Read plugin.json
    plugin_json_path = plugin_dir / 'plugin.json'
    if not plugin_json_path.exists():
        print(f'Error: {plugin_json_path} not found')
        sys.exit(1)

    with open(plugin_json_path, 'r', encoding='utf-8') as f:
        plugin_meta = json.load(f)

    PLUGIN_VERSION = version_override or plugin_meta.get('version', '0.1.0')
    tag = f'{identifier}-v{PLUGIN_VERSION}'
    release_name = f'{plugin_meta.get("name", identifier)} v{PLUGIN_VERSION}'

    if not TOKEN:
        print('Error: GITHUB_TOKEN environment variable not set')
        print('  Generate one at: https://github.com/settings/tokens')
        print('  Required scope: repo')
        sys.exit(1)

    print(f'Publishing {identifier} v{PLUGIN_VERSION}...')
    print(f'  Plugin dir: {plugin_dir}')
    print(f'  Target repo: {REPO}')
    print()

    # Step 1: Package plugin
    print('1. Packaging plugin...')
    zip_path, file_size = _zip_plugin(identifier, plugin_dir)
    sha256 = _sha256_file(zip_path)
    zip_filename = os.path.basename(zip_path)
    print(f'   Zip: {zip_filename} ({file_size:,} bytes)')
    print(f'   SHA256: {sha256}')
    print()

    # Step 2: Create GitHub Release
    print('2. Creating GitHub Release...')
    try:
        release = _create_release(tag, release_name,
                                  f'{plugin_meta.get("description", "")}\n\nSHA256: `{sha256}`')
    except RuntimeError as e:
        # Release might already exist — try to get it
        if 'already_exists' in str(e) or '422' in str(e):
            print(f'   Release {tag} already exists, fetching...')
            release = _api_request('GET', f'/releases/tags/{tag}')
        else:
            raise

    release_id = release['id']
    html_url = release.get('html_url', '')
    print(f'   Release: {html_url}')
    print()

    # Step 3: Upload zip asset
    print('3. Uploading asset...')
    _upload_asset(release_id, zip_path, zip_filename)
    download_url = f'https://github.com/{REPO}/releases/download/{tag}/{zip_filename}'
    print(f'   Download URL: {download_url}')
    print()

    # Step 4: Build plugin catalog entry
    print('4. Building catalog entry...')
    entry = {
        'identifier': identifier,
        'name': plugin_meta.get('name', identifier),
        'description': plugin_meta.get('description', ''),
        'version': PLUGIN_VERSION,
        'author': plugin_meta.get('author', ''),
        'author_url': plugin_meta.get('author_url', ''),
        'icon_url': plugin_meta.get('icon_url', ''),
        'price_type': plugin_meta.get('price_type', 'free'),
        'price_amount': plugin_meta.get('price_amount', 0),
        'price_interval': plugin_meta.get('price_interval', 'onetime'),
        'trial_days': plugin_meta.get('trial_days', 0),
        'download_url': download_url,
        'package_hash': sha256,
        'file_size': file_size,
        'category': plugin_meta.get('category', ''),
        'tags': plugin_meta.get('tags', []),
        'min_app_version': plugin_meta.get('min_app_version', '0.10.0'),
        'depends_on': plugin_meta.get('depends_on', {}),
        'screenshots': plugin_meta.get('screenshots', []),
        'readme_url': plugin_meta.get('readme_url', ''),
    }
    print(f'   Entry: {json.dumps(entry, indent=2, ensure_ascii=False)}')
    print()

    # Step 5: Update store_catalog.json
    print('5. Updating store_catalog.json...')
    catalog, catalog_sha = _get_catalog()
    _update_catalog(catalog, catalog_sha, entry, identifier)

    # Cleanup temp files
    shutil.rmtree(os.path.dirname(zip_path), ignore_errors=True)

    print()
    print(f'Done! {identifier} v{PLUGIN_VERSION} published.')
    print(f'  Release: {html_url}')
    print(f'  Download: {download_url}')


if __name__ == '__main__':
    main()