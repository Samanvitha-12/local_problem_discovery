"""
Download datasets listed in backend/datasets/dataset_list.yml.
Supports entries with either a "kaggle_slug" (download via Kaggle CLI) or a direct "url".

Provide Kaggle credentials via env vars only when using Kaggle slugs:
  KAGGLE_USERNAME and KAGGLE_KEY

Install prerequisites in the backend virtualenv:
  pip install -r requirements.txt

Usage:
  python scripts/download_kaggle_datasets.py

Downloads are placed under backend/datasets/raw/<identifier>/
A download_manifest.yaml is written to backend/datasets/ with status info.
"""
import os
import re
import sys
import subprocess
import yaml
import shutil
import zipfile
import tempfile
from pathlib import Path

try:
    import requests
except Exception:
    requests = None

ROOT = Path(__file__).resolve().parents[1]
DATASETS_DIR = ROOT / 'datasets'
RAW_DIR = DATASETS_DIR / 'raw'
MANIFEST = DATASETS_DIR / 'download_manifest.yaml'


def load_list():
    cfg = DATASETS_DIR / 'dataset_list.yml'
    if not cfg.exists():
        print(f"Dataset list not found: {cfg}. Create one based on dataset_list.yml.example")
        sys.exit(1)
    with cfg.open('r', encoding='utf-8') as fh:
        return yaml.safe_load(fh) or []


def ensure_env_if_needed(items):
    # If any item uses a kaggle_slug, require Kaggle credentials
    needs_kaggle = any(item.get('kaggle_slug') for item in items)
    if needs_kaggle:
        if not os.environ.get('KAGGLE_USERNAME') or not os.environ.get('KAGGLE_KEY'):
            print('At least one dataset requires Kaggle credentials. Set KAGGLE_USERNAME and KAGGLE_KEY before running.')
            print('See backend/datasets/README.md for details.')
            sys.exit(2)


def download_kaggle_dataset(slug, dest: Path):
    dest.mkdir(parents=True, exist_ok=True)
    print(f"Downloading Kaggle dataset {slug} -> {dest}")
    try:
        subprocess.run(['kaggle', 'datasets', 'download', '-d', slug, '-p', str(dest), '--unzip', '--force'], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to download {slug}: {e}")
        return False


def make_safe_folder_name(value: str) -> str:
    value = re.sub(r'[^A-Za-z0-9._-]+', '_', value).strip('._-')
    return value or 'dataset'


def download_url(url, dest: Path):
    dest.mkdir(parents=True, exist_ok=True)
    print(f"Fetching URL {url} -> {dest}")
    # Prefer git clone for GitHub repos
    if 'github.com' in url and shutil.which('git'):
        try:
            subprocess.run(['git', 'clone', '--depth', '1', url, str(dest)], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"git clone failed for {url}: {e}")
            # fall through to HTTP download
    if requests is None:
        print('The requests package is not available. Install requirements.txt before running URL downloads.')
        return False
    try:
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            # If it looks like a zip, save and extract
            content_type = r.headers.get('Content-Type', '')
            if url.lower().endswith('.zip') or 'zip' in content_type:
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    for chunk in r.iter_content(chunk_size=8192):
                        tmp.write(chunk)
                    tmp_path = tmp.name
                try:
                    with zipfile.ZipFile(tmp_path, 'r') as zf:
                        zf.extractall(path=str(dest))
                    os.unlink(tmp_path)
                    return True
                except zipfile.BadZipFile:
                    print(f"Downloaded file from {url} is not a valid zip archive")
                    return False
            # Otherwise save as single file
            filename = url.split('/')[-1] or 'downloaded_file'
            out_path = dest / filename
            with open(out_path, 'wb') as fh:
                for chunk in r.iter_content(chunk_size=8192):
                    fh.write(chunk)
            return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False


def main():
    items = load_list()
    if not items:
        print('No datasets defined in dataset_list.yml')
        return
    ensure_env_if_needed(items)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    for item in items:
        name = item.get('name') or item.get('slug') or item.get('kaggle_slug') or item.get('url')
        kaggle_slug = item.get('kaggle_slug')
        url = item.get('url')
        ident = make_safe_folder_name(kaggle_slug or url or name)
        dest = RAW_DIR / ident
        ok = False
        source = None
        if kaggle_slug:
            ok = download_kaggle_dataset(kaggle_slug, dest)
            source = {'type': 'kaggle', 'spec': kaggle_slug}
        elif url:
            ok = download_url(url, dest)
            source = {'type': 'url', 'spec': url}
        else:
            print(f"Skipping entry without kaggle_slug or url: {name}")
            manifest.append({'name': name, 'destination': str(dest), 'downloaded': False, 'reason': 'no source'})
            continue
        manifest.append({'name': name, 'destination': str(dest), 'downloaded': bool(ok), 'source': source})
    with MANIFEST.open('w', encoding='utf-8') as fh:
        yaml.safe_dump(manifest, fh, sort_keys=False, allow_unicode=True)
    print('Download complete. See', MANIFEST)


if __name__ == '__main__':
    main()
