"""Automatic updater for hallpass-qt on Debian.

Mirrors the one-command installer (scripts/install_debian.sh): fetches the
latest GitHub tag, builds the .deb from that tagged source with
scripts/build_deb.sh, then installs it with apt. All network is HTTPS-only to
github.com / api.github.com. Requires root for the apt install step — the
kiosk user needs a sudoers NOPASSWD entry for apt (documented in README).

Quota: 0 = disabled. Runs on a background thread so the kiosk never blocks.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tarfile
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO = "sb-lhs/bathroom-pass-app"
GITHUB_API = f"https://api.github.com/repos/{REPO}"
RAW_BASE = f"https://github.com/{REPO}"


def _version_tuple(v: str) -> tuple[int, ...]:
    s = str(v).strip().lower()
    if s.startswith("v"):
        s = s[1:]
    parts = re.split(r"[.\-_]", s)
    nums: list[int] = []
    for p in parts:
        m = re.match(r"^(\d+)$", p or "")
        nums.append(int(m.group(1)) if m else 0)
    while len(nums) < 4:
        nums.append(0)
    return tuple(nums[:4])


def installed_version() -> str:
    try:
        from hallpass import __version__ as v  # type: ignore
        return str(v)
    except Exception:
        return "0.0.0"


def fetch_latest_tag(timeout: int = 15) -> str | None:
    """Highest semver tag on GitHub (HTTPS only)."""
    url = GITHUB_API + "/tags?per_page=50"
    req = urllib.request.Request(url, headers={"User-Agent": "hallpass-qt-updater"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    if not isinstance(data, list):
        return None
    best: str | None = None
    best_key: tuple[int, ...] = (0, 0, 0, 0)
    for item in data:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        if not name:
            continue
        key = _version_tuple(name)
        if key > best_key:
            best_key = key
            best = name
    return best


def is_newer(remote: str, local: str) -> bool:
    return _version_tuple(remote) > _version_tuple(local)


@dataclass
class UpdateResult:
    ok: bool
    version: str = ""
    message: str = ""
    deb_path: str = ""


def download_source(version: str, dest_dir: str | None = None, timeout: int = 60) -> str:
    tag = version if version.startswith("v") else "v" + version
    url = f"{RAW_BASE}/archive/refs/tags/{tag}.tar.gz"
    req = urllib.request.Request(url, headers={"User-Agent": "hallpass-qt-updater"})
    work = Path(dest_dir or tempfile.mkdtemp(prefix="hallpass-update-"))
    work.mkdir(parents=True, exist_ok=True)
    tarball = work / f"hallpass-{tag}.tar.gz"
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        tarball.write_bytes(resp.read())
    return str(tarball)


def extract_tarball(tarball: str, dest_dir: str) -> str:
    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    with tarfile.open(tarball, "r:gz") as tf:
        tf.extractall(dest_dir)
    # The archive contains a single top-level dir: bathroom-pass-app-<tag>
    entries = [p for p in Path(dest_dir).iterdir() if p.is_dir()]
    if not entries:
        raise RuntimeError("extracted archive has no source directory")
    return str(entries[0])


def build_deb(src_dir: str, timeout: int = 300) -> str:
    script = str(Path(src_dir) / "scripts" / "build_deb.sh")
    if not Path(script).exists():
        raise RuntimeError("build_deb.sh not found in extracted source")
    env = dict(os.environ)
    env.setdefault("DEBIAN_FRONTEND", "noninteractive")
    subprocess.run(["bash", script], cwd=src_dir, check=True, env=env, timeout=timeout)
    # build_deb.sh writes <root>/hallpass-qt_<ver>_amd64.deb
    version = installed_version()
    # Re-derive version from control file inside src for accuracy
    control = Path(src_dir) / "DEBIAN" / "control"
    ver = version
    if control.exists():
        for line in control.read_text(encoding="utf-8").splitlines():
            if line.startswith("Version:"):
                ver = line.split(":", 1)[1].strip()
                break
    deb = str(Path(src_dir) / f"hallpass-qt_{ver}_amd64.deb")
    if not Path(deb).exists():
        # Fallback: find the newest deb in src root
        debs = sorted(Path(src_dir).glob("hallpass-qt_*_amd64.deb"), key=lambda p: p.stat().st_mtime)
        if not debs:
            raise RuntimeError("no .deb produced by build")
        deb = str(debs[-1])
    return deb


def install_deb(deb_path: str, timeout: int = 300) -> UpdateResult:
    """Install the .deb with apt (needs root). Tries sudo, falls back to direct."""
    cmd = ["sudo", "-n", "apt-get", "install", "-y", deb_path]
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=timeout)
        if proc.returncode == 0:
            return UpdateResult(ok=True, message="installed via sudo apt")
        # sudo may not be configured; try direct (running as root)
        proc2 = subprocess.run(["apt-get", "install", "-y", deb_path], check=False, capture_output=True, text=True, timeout=timeout)
        if proc2.returncode == 0:
            return UpdateResult(ok=True, message="installed via apt")
        tail = (proc.stderr or proc2.stderr or "")[-800:]
        return UpdateResult(ok=False, message=f"apt install failed: {tail}")
    except FileNotFoundError:
        return UpdateResult(ok=False, message="apt-get not found")
    except subprocess.TimeoutExpired:
        return UpdateResult(ok=False, message="apt install timed out")


def perform_update(version: str | None = None, timeout: int = 600) -> UpdateResult:
    """Full update: check (if version None), download, build, install."""
    try:
        if version is None:
            remote = fetch_latest_tag()
            if remote is None:
                return UpdateResult(ok=False, message="could not reach GitHub")
            local = installed_version()
            if not is_newer(remote, local):
                return UpdateResult(ok=True, version=local, message="already up to date")
            version = remote
        work = tempfile.mkdtemp(prefix="hallpass-update-")
        tarball = download_source(version, work)
        src_dir = extract_tarball(tarball, work)
        deb = build_deb(src_dir, timeout=timeout)
        return install_deb(deb, timeout=timeout)
    except Exception as e:
        return UpdateResult(ok=False, message=f"update failed: {e}")
