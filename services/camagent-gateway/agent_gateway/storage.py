"""Rasm saqlash interfeysi.

Ikki implementatsiya: `DiskStorage` (dev, standart) va `S3Storage`
(ishlab chiqarish — SeaweedFS/MinIO/AWS, bazada faqat havola saqlanadi).
Tanlov muhitdan: `storage_from_env()`.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from pathlib import Path

log = logging.getLogger("agent_gateway.storage")


class SnapshotStorage:
    """save_snapshot() interfeysi — sbozor S3 backend'ni shu imzo bilan yozadi."""

    def save_snapshot(self, key: str, jpeg: bytes, meta: dict) -> str:
        """Rasmni saqlaydi, havola (storage ref) qaytaradi."""
        raise NotImplementedError

    def open_snapshot(self, ref: str) -> bytes:
        raise NotImplementedError


def _safe(name: str) -> str:
    """Fayl nomi uchun xavfsiz satr.

    DIQQAT: yo'l traversali komponenti (`.`, `..`) HOSIL BO'LMASLIGI kerak.
    Audit topilmasi: `X-Agent-Time=".."` → `day=".."` → `root/../...` ga,
    ya'ni saqlash papkasidan TASHQARIGA yozilardi. Nuqta ruxsat etiladi
    (sana `2026-08-26` kabi), lekin natija faqat nuqtadan iborat bo'lsa
    xavfsiz nomga almashtiriladi.
    """
    toza = re.sub(r"[^A-Za-z0-9._-]", "_", name or "")
    if toza.strip(".") == "":        # "", ".", ".." — traversal
        return "_"
    return toza


class DiskStorage(SnapshotStorage):
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save_snapshot(self, key: str, jpeg: bytes, meta: dict) -> str:
        day = (meta.get("agent_time") or "unknown")[:10] or "unknown"
        digest = hashlib.sha256(key.encode()).hexdigest()[:16]
        rel = Path(_safe(day)) / f"{_safe(key)[:80]}_{digest}.jpg"
        path = (self.root / rel).resolve()
        # Ikkinchi qatlam: nima bo'lganda ham saqlash papkasidan chiqmasin.
        if self.root != path.parent and self.root not in path.parents:
            raise PermissionError("storage tashqarisiga yozishga urinish")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(jpeg)
        # Sidecar: rasmning kimga/qachon/qaysi kameraga tegishli ekani
        # faylning O'ZI bilan yonma-yon yotsin. Bazasiz bu rasm shunchaki
        # JPEG — kanal ham, vaqt ham, seriya raqami ham yo'q, dalil sifatida
        # qiymati yo'qoladi. Baza tiklanganda indeks shulardan qayta
        # yig'iladi.
        try:
            path.with_suffix(".json").write_text(
                json.dumps({"key": key, "size": len(jpeg), **meta},
                           ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass          # sidecar yozilmasa ham rasm saqlangan — yo'qotmaymiz
        return str(rel).replace("\\", "/")

    def open_snapshot(self, ref: str) -> bytes:
        path = (self.root / ref).resolve()
        if self.root.resolve() not in path.parents and path != self.root.resolve():
            raise PermissionError("storage tashqarisiga murojaat")
        return path.read_bytes()


class S3Storage(SnapshotStorage):
    """S3-mos obyekt xotira (SeaweedFS, MinIO, AWS S3).

    Havola shakli: `s3://{bucket}/{obyekt_kaliti}` — bazadagi `storage_ref`
    shu satr bo'ladi, `open_snapshot` uni qayta ochadi.

    Diskdagi bilan bir xil ikki qoida saqlanadi:
      * obyekt kaliti FAQAT `_safe()` dan o'tgan bo'laklardan quriladi —
        traversal ham, erkin matn ham kalitga tushmaydi;
      * har rasm yoniga `.json` sidecar yoziladi — bazasiz rasm shunchaki
        JPEG bo'lib qolmasin (docs/integration.md 3-bo'lim talabi).

    `client` sinovlarda qo'lda beriladi (duck-typing: `put_object` /
    `get_object`); ishlab chiqarishda `boto3` dan yasaladi. `boto3` import
    KECHIKTIRILGAN — disk rejimida ishlaydigan o'rnatma bu paketni umuman
    talab qilmaydi.
    """

    def __init__(self, bucket: str, endpoint_url: str = "",
                 access_key: str = "", secret_key: str = "",
                 region: str = "us-east-1", prefix: str = "",
                 client=None):
        if not bucket:
            raise ValueError("S3 bucket nomi bo'sh bo'lishi mumkin emas")
        self.bucket = bucket
        self.prefix = (prefix or "").strip("/")
        if client is None:
            import boto3                              # kechiktirilgan import
            from botocore.config import Config
            client = boto3.client(
                "s3",
                endpoint_url=endpoint_url or None,
                aws_access_key_id=access_key or None,
                aws_secret_access_key=secret_key or None,
                region_name=region or "us-east-1",
                config=Config(
                    connect_timeout=10, read_timeout=30,
                    retries={"max_attempts": 3, "mode": "standard"},
                    # SeaweedFS/MinIO virtual-host uslubini bilmaydi.
                    s3={"addressing_style": "path"}),
            )
        self.client = client

    def _object_key(self, key: str, meta: dict) -> str:
        day = _safe((meta.get("agent_time") or "unknown")[:10] or "unknown")
        digest = hashlib.sha256(key.encode()).hexdigest()[:16]
        name = f"{_safe(key)[:80]}_{digest}"
        return "/".join(p for p in (self.prefix, day, name) if p)

    def save_snapshot(self, key: str, jpeg: bytes, meta: dict) -> str:
        obj = self._object_key(key, meta) + ".jpg"
        self.client.put_object(Bucket=self.bucket, Key=obj, Body=jpeg,
                               ContentType="image/jpeg")
        try:
            self.client.put_object(
                Bucket=self.bucket, Key=obj[:-len(".jpg")] + ".json",
                Body=json.dumps({"key": key, "size": len(jpeg), **meta},
                                ensure_ascii=False).encode("utf-8"),
                ContentType="application/json")
        except Exception:                             # noqa: BLE001
            # Sidecar yozilmasa ham rasm saqlangan — dalilni yo'qotmaymiz.
            log.warning("S3 sidecar yozilmadi: %s", obj)
        return f"s3://{self.bucket}/{obj}"

    def open_snapshot(self, ref: str) -> bytes:
        if not ref.startswith("s3://"):
            raise PermissionError("S3 bo'lmagan havola")
        bucket, _, obj = ref[len("s3://"):].partition("/")
        if bucket != self.bucket or not obj:
            # Panel ref'ni so'rovdan oladi — begona bucket'ga chiqib
            # ketmasin (DiskStorage'dagi containment tekshiruvi bilan
            # bir xil chegara).
            raise PermissionError("begona bucket yoki bo'sh kalit")
        resp = self.client.get_object(Bucket=self.bucket, Key=obj)
        return resp["Body"].read()


def storage_from_env(data_dir: Path) -> SnapshotStorage:
    """Muhit o'zgaruvchilaridan saqlash backend'ini tanlaydi.

    `CAMAGENT_GW_S3_BUCKET` berilgan bo'lsa — S3, aks holda disk.
    S3 tanlangan-u kalitlar yetishmasa — YIQILADI (jimgina disk rejimiga
    tushish "hammasi ishlayapti" degan yolg'on taassurot berardi va
    rasmlar konteyner diskida to'planib borardi).
    """
    bucket = os.environ.get("CAMAGENT_GW_S3_BUCKET", "").strip()
    if not bucket:
        return DiskStorage(Path(data_dir) / "snapshots")
    return S3Storage(
        bucket=bucket,
        endpoint_url=os.environ.get("CAMAGENT_GW_S3_ENDPOINT", "").strip(),
        access_key=os.environ.get("CAMAGENT_GW_S3_ACCESS_KEY", "").strip(),
        secret_key=os.environ.get("CAMAGENT_GW_S3_SECRET_KEY", "").strip(),
        region=os.environ.get("CAMAGENT_GW_S3_REGION", "us-east-1").strip(),
        prefix=os.environ.get("CAMAGENT_GW_S3_PREFIX", "").strip(),
    )
