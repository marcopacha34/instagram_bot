"""Cihaz lisansi - kendi barindirdigimiz PHP/MySQL lisans sunucusuyla konusur."""

from __future__ import annotations

import base64
import ctypes
import hashlib
import json
import os
import platform
import urllib.error
import urllib.parse
import urllib.request
import winreg
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


LISANS_API_KOKU = "https://burakhoca.com/lisans/api"
CEVRIMDISI_GUN = 7


def veri_klasoru() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path(__file__).parent))
    folder = base / "BurakHocaInstagramPaneli"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.c_ulong),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def _blob(data: bytes) -> tuple[_DataBlob, ctypes.Array]:
    buffer = ctypes.create_string_buffer(data)
    value = _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    return value, buffer


def dpapi_sifrele(data: bytes) -> bytes:
    source, source_buffer = _blob(data)
    output = _DataBlob()
    entropy, entropy_buffer = _blob(b"BurakHocaInstagramPaneli-v1")
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(source),
        "Burak Hoca Lisans",
        ctypes.byref(entropy),
        None,
        None,
        0,
        ctypes.byref(output),
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        del source_buffer, entropy_buffer
        ctypes.windll.kernel32.LocalFree(output.pbData)


def dpapi_coz(data: bytes) -> bytes:
    source, source_buffer = _blob(data)
    output = _DataBlob()
    entropy, entropy_buffer = _blob(b"BurakHocaInstagramPaneli-v1")
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(source),
        None,
        ctypes.byref(entropy),
        None,
        None,
        0,
        ctypes.byref(output),
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        del source_buffer, entropy_buffer
        ctypes.windll.kernel32.LocalFree(output.pbData)


def cihaz_parmak_izi() -> str:
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography"
        ) as key:
            machine_guid = str(winreg.QueryValueEx(key, "MachineGuid")[0])
    except OSError:
        machine_guid = platform.node()
    material = f"burakhoca-v1|{machine_guid}|{platform.machine()}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _istek(endpoint: str, fields: dict[str, str], timeout: int = 20) -> dict:
    request = urllib.request.Request(
        f"{LISANS_API_KOKU}/{endpoint}",
        data=urllib.parse.urlencode(fields).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "BurakHocaInstagramPaneli/3.5",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8", errors="replace"))
            message = payload.get("mesaj") or payload.get("hata") or f"Sunucu hatasi ({exc.code})"
        except ValueError:
            message = f"Sunucu hatasi ({exc.code})"
        raise RuntimeError(str(message)) from exc
    except urllib.error.URLError as exc:
        raise ConnectionError("Lisans sunucusuna baglanilamadi.") from exc


@dataclass
class LisansDurumu:
    gecerli: bool
    mesaj: str
    musteri: str = ""
    sona_erme: str = ""


_DOGRULAMA_NEDENLERI = {
    "kaldirilmis": "Lisans bu cihazdan kaldirilmis.",
    "iptal_edilmis": "Lisans iptal edilmis.",
    "suresi_dolmus": "Lisansin suresi dolmus.",
    "cihaz_uyusmuyor": "Bu lisans baska bir cihaza kayitli.",
    "bulunamadi": "Lisans kaydi bulunamadi.",
    "eksik_alan": "Lisans kaydi eksik, yeniden etkinlestirin.",
}


class LisansYoneticisi:
    def __init__(self) -> None:
        self.path = veri_klasoru() / "lisans.dat"

    def _kaydet(self, payload: dict) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        encoded = base64.b64encode(dpapi_sifrele(raw))
        temp = self.path.with_suffix(".tmp")
        temp.write_bytes(encoded)
        temp.replace(self.path)

    def _oku(self) -> dict:
        try:
            encrypted = base64.b64decode(self.path.read_bytes(), validate=True)
            return json.loads(dpapi_coz(encrypted).decode("utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return {}

    def kayitli_bilgi(self) -> dict:
        """Ağ isteği yapmadan bu cihazda kayıtlı son lisans bilgisini döndürür."""
        return self._oku()

    def etkinlestir(self, key: str) -> LisansDurumu:
        key = key.strip().upper()
        if len(key) < 10:
            return LisansDurumu(False, "Gecerli bir lisans anahtari girin.")
        fingerprint = cihaz_parmak_izi()
        payload = _istek(
            "activate.php",
            {
                "license_key": key,
                "fingerprint": fingerprint,
                "device_name": f"PC-{platform.node()}"[:190],
            },
        )
        if not payload.get("ok"):
            return LisansDurumu(
                False, str(payload.get("mesaj") or payload.get("hata") or "Aktivasyon reddedildi.")
            )
        musteri = str(payload.get("musteri_adi") or "")
        sona_erme = str(payload.get("son_kullanma") or "")
        self._kaydet(
            {
                "license_key": key,
                "activation_id": payload.get("activation_id"),
                "fingerprint": fingerprint,
                "last_verified": datetime.now(timezone.utc).isoformat(),
                "musteri_adi": musteri,
                "son_kullanma": sona_erme,
            }
        )
        return LisansDurumu(
            True, str(payload.get("mesaj") or "Lisans basariyla etkinlestirildi."), musteri, sona_erme
        )

    def dogrula(self, internet_zorunlu: bool = False) -> LisansDurumu:
        saved = self._oku()
        if not saved:
            return LisansDurumu(False, "Bu bilgisayarda etkin bir lisans bulunamadi.")
        fingerprint = cihaz_parmak_izi()
        if saved.get("fingerprint") != fingerprint:
            return LisansDurumu(False, "Lisans bu bilgisayara ait degil.")
        try:
            payload = _istek(
                "validate.php",
                {
                    "license_key": str(saved.get("license_key", "")),
                    "activation_id": str(saved.get("activation_id", "")),
                    "fingerprint": fingerprint,
                },
            )
            if not payload.get("valid"):
                neden = _DOGRULAMA_NEDENLERI.get(str(payload.get("neden", "")), "Lisans gecersiz.")
                return LisansDurumu(False, neden)
            saved["last_verified"] = datetime.now(timezone.utc).isoformat()
            saved["musteri_adi"] = payload.get("musteri_adi", saved.get("musteri_adi", ""))
            saved["son_kullanma"] = payload.get("son_kullanma") or saved.get("son_kullanma", "")
            self._kaydet(saved)
            return LisansDurumu(
                True, "Lisans dogrulandi.", str(saved.get("musteri_adi") or ""), str(saved.get("son_kullanma") or "")
            )
        except ConnectionError:
            if internet_zorunlu:
                return LisansDurumu(False, "Lisans dogrulamasi icin internet baglantisi gerekli.")
            try:
                last = datetime.fromisoformat(str(saved.get("last_verified")))
            except (TypeError, ValueError):
                return LisansDurumu(False, "Lisans dogrulanamadi; internete baglanin.")
            if datetime.now(timezone.utc) - last <= timedelta(days=CEVRIMDISI_GUN):
                return LisansDurumu(True, "Cevrimdisi lisans suresi kullaniliyor.")
            return LisansDurumu(False, "Cevrimdisi kullanim suresi doldu; internete baglanin.")
        except RuntimeError as exc:
            return LisansDurumu(False, str(exc))

    def kaldir(self) -> LisansDurumu:
        saved = self._oku()
        if not saved:
            return LisansDurumu(False, "Kaldirilacak lisans bulunamadi.")
        try:
            payload = _istek(
                "deactivate.php",
                {
                    "license_key": str(saved.get("license_key", "")),
                    "activation_id": str(saved.get("activation_id", "")),
                    "fingerprint": str(saved.get("fingerprint", "")),
                },
            )
            if not payload.get("ok"):
                return LisansDurumu(
                    False, str(payload.get("mesaj") or payload.get("hata") or "Lisans kaldirilamadi.")
                )
            self.path.unlink(missing_ok=True)
            return LisansDurumu(True, "Lisans bu bilgisayardan kaldirildi.")
        except (ConnectionError, RuntimeError) as exc:
            return LisansDurumu(False, str(exc))
