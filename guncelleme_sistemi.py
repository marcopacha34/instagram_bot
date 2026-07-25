"""Güvenli GitHub sürüm güncellemesi."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path


GITHUB_DEPOSU = "marcopacha34/instagram_bot"


def surum_parcala(value: str) -> tuple[int, ...]:
    value = value.strip().lstrip("vV").split("-", 1)[0]
    try:
        return tuple(int(part) for part in value.split("."))
    except ValueError:
        return (0,)


class GuncellemeYoneticisi:
    def __init__(self, mevcut_surum: str) -> None:
        self.mevcut_surum = mevcut_surum

    def son_surumu_getir(self) -> dict | None:
        request = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_DEPOSU}/releases/latest",
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "BurakHocaInstagramPaneli-Updater",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                release = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError):
            return None
        if surum_parcala(str(release.get("tag_name", ""))) <= surum_parcala(
            self.mevcut_surum
        ):
            return None
        asset = next(
            (
                item
                for item in release.get("assets", [])
                if item.get("name") == "BurakHoca_InstagramPaneli_Setup.exe"
            ),
            None,
        )
        if not asset or not str(asset.get("digest", "")).startswith("sha256:"):
            return None
        return {
            "version": str(release.get("tag_name", "")).lstrip("vV"),
            "notes": str(release.get("body") or ""),
            "url": str(asset.get("browser_download_url") or ""),
            "sha256": str(asset["digest"]).split(":", 1)[1].lower(),
        }

    @staticmethod
    def indir(release: dict, progress=None) -> Path:
        target = Path(tempfile.gettempdir()) / (
            f"BurakHoca_InstagramPaneli_Setup_{release['version']}.exe"
        )
        request = urllib.request.Request(
            release["url"], headers={"User-Agent": "BurakHocaInstagramPaneli-Updater"}
        )
        digest = hashlib.sha256()
        with urllib.request.urlopen(request, timeout=60) as response, target.open("wb") as output:
            total = int(response.headers.get("Content-Length", "0") or 0)
            received = 0
            while True:
                block = response.read(1024 * 256)
                if not block:
                    break
                output.write(block)
                digest.update(block)
                received += len(block)
                if progress and total:
                    progress(min(100, int(received * 100 / total)))
        if digest.hexdigest().lower() != release["sha256"]:
            target.unlink(missing_ok=True)
            raise RuntimeError("Güncelleme dosyasının SHA-256 doğrulaması başarısız.")
        return target

    @staticmethod
    def kurulumu_baslat(path: Path) -> None:
        subprocess.Popen(
            [str(path), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
            close_fds=True,
        )
