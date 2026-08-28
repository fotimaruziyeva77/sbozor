"""CamAgent -> sbozor bazasiga sinxronizatsiya.

=============================================================================
NEGA BU MODUL BOR
=============================================================================

CamAgent va sbozor kameralarni IKKI XIL yo'l bilan ko'radi:

  · sbozor  — SERVER-PULL: server bozor tarmog'iga o'zi ulanadi
              (`nvr_devices` + `/discover`). Bu tunnel talab qiladi.
  · CamAgent — AGENT-PUSH: agent tashqariga o'zi chiqadi, tunnel kerak emas.

Obyektda tunnel yo'q, ya'ni sbozor `discover` hech qachon ishlamaydi va
uning kameralar ro'yxati BO'SH qoladi — holbuki agent o'sha kameralarni
allaqachon topgan, ulangan va kadr olayotgan bo'ladi. Operator uchun bu
«ikkita tizim, ikkita ro'yxat» degani.

Bu modul agent BILGANINI sbozor jadvallariga yozadi: `nvr_devices`,
`cameras` va (kadr kelganda) `snapshots`. Discovery O'TKAZIB YUBORILADI —
uni agent allaqachon bajargan.

=============================================================================
⛔⛔ CHEGARA: FAQAT YOZISH, HECH QANDAY BIZNES MANTIQ
=============================================================================

CLAUDE.md 2-bo'limining 2-prinsipi: «Agent bozor mantiqini bilmaydi».
Bu modul ham bilmaydi — u faqat qurilma faktlarini ko'chiradi (IP, seriya,
kanal, kadr havolasi). Rasta, zona, tarif, to'lov — hammasi sbozor
tomonida qoladi.

⚠ `market_id` — aktivatsiya kodidagi `key_prefix`. Kod yaratilganda u
  yerga sbozor bozorining UUID'si yoziladi (`docs/integration.md` §3.4).
  UUID bo'lmasa sinxronizatsiya JIMGINA o'tkazib yuboriladi: eski
  kodlar bilan ishlaydigan obyektlar buzilmasin.

⚠ ULANISH IXTIYORIY: `CAMAGENT_SBOZOR_DSN` berilmagan bo'lsa modul
  butunlay o'chadi va gateway o'zicha ishlayveradi. CamAgent boshqa
  loyihalarda ham ishlatiladi — u sbozor'siz ham to'liq ishlashi shart.
"""
from __future__ import annotations

import logging
import os
import re
import uuid
from typing import Any

log = logging.getLogger("agent_gateway.sbozor")

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)

# Kanal nomi bo'sh bo'lsa shu ishlatiladi — `cameras.name` NOT NULL.
_NOMSIZ = "kamera"


def market_id_from_prefix(key_prefix: str) -> str | None:
    """`key_prefix` sbozor bozorining UUID'simi.

    Eski obyektlarda u `karmana-01` kabi qisqa yorliq bo'lishi mumkin —
    bunday holatda sinxronizatsiya o'tkazib yuboriladi (`None`).
    """
    qiymat = (key_prefix or "").strip()
    return qiymat if _UUID_RE.match(qiymat) else None


class SbozorSync:
    """sbozor PostgreSQL'iga yozadigan yupqa qatlam.

    ⛔ XATO YUTILADI VA JURNALGA YOZILADI. Sinxronizatsiya — QO'SHIMCHA
       qulaylik; u yiqilsa ham agent kadr olishda davom etishi shart
       (CLAUDE.md 4-prinsip: «rasm olish o'tkazib yuborilmaydi»).
    """

    def __init__(self, dsn: str = ""):
        self.dsn = dsn or os.environ.get("CAMAGENT_SBOZOR_DSN", "")
        self._psycopg: Any = None
        if not self.dsn:
            log.info("sbozor sinxronizatsiyasi o'chiq (CAMAGENT_SBOZOR_DSN yo'q)")
            return
        try:
            import psycopg                       # type: ignore[import-not-found]

            self._psycopg = psycopg
            log.info("sbozor sinxronizatsiyasi yoqildi")
        except ImportError:
            log.warning("psycopg o'rnatilmagan — sbozor sinxronizatsiyasi o'chiq")

    @property
    def enabled(self) -> bool:
        return bool(self.dsn and self._psycopg)

    # ------------------------------------------------ qurilmalar

    def sync_devices(self, key_prefix: str, nvrs: list[dict]) -> int:
        """Agent topgan qurilmalarni `nvr_devices` + `cameras` ga yozadi.

        Idempotent: qayta chaqirilganda mavjud yozuvlar YANGILANADI
        (`ON CONFLICT`), yangi kanal qo'shilsa qo'shiladi. Agent har
        `register` da chaqiradi, ya'ni kamera qo'shilgan kuni sbozor
        ro'yxati o'zi to'g'rilanadi.

        Returns: yozilgan kanallar soni.
        """
        market_id = market_id_from_prefix(key_prefix)
        if not (self.enabled and market_id and nvrs):
            return 0
        try:
            with self._psycopg.connect(self.dsn, autocommit=False) as conn:
                with conn.cursor() as cur:
                    return self._sync_devices(cur, market_id, nvrs)
        except Exception as exc:                  # noqa: BLE001 — qulaylik qatlami
            log.warning("sbozor sinxronizatsiyasi yiqildi: %s", exc)
            return 0

    def _sync_devices(self, cur: Any, market_id: str, nvrs: list[dict]) -> int:
        yozildi = 0
        for nvr in nvrs:
            ip = str(nvr.get("ip") or "").strip()
            if not ip:
                continue
            seriya = str(nvr.get("serial") or "") or None
            model = str(nvr.get("model") or "") or None
            proshivka = str(nvr.get("firmware") or "") or None

            # ⛔ `capture_method='isapi'`: sbozor go2rtc orqali kadr
            #    olmaydi (u kameraga yeta olmaydi) — kadrlarni AGENT
            #    yuboradi. Bu qiymat «kim olgani» ni hujjatlashtiradi.
            cur.execute(
                """
                INSERT INTO nvr_devices
                    (market_id, host, port, username, model, serial_number,
                     firmware_version, device_type, last_discovery_at,
                     capture_method)
                VALUES (%s, %s, 80, 'camagent', %s, %s, %s, 'camera', now(),
                        'isapi')
                ON CONFLICT (market_id, host, port) DO UPDATE SET
                    model            = COALESCE(EXCLUDED.model, nvr_devices.model),
                    serial_number    = COALESCE(EXCLUDED.serial_number,
                                                nvr_devices.serial_number),
                    firmware_version = COALESCE(EXCLUDED.firmware_version,
                                                nvr_devices.firmware_version),
                    last_discovery_at = now(),
                    updated_at        = now()
                RETURNING id
                """,
                (market_id, ip, model, seriya, proshivka),
            )
            qator = cur.fetchone()
            if not qator:
                continue
            nvr_id = qator[0]

            for kanal in nvr.get("channels") or []:
                ch = int(kanal.get("id") or 0)
                # ⚠ O'CHIRILGAN KANAL YOZILMAYDI: operator uni panelda
                #   o'chirgan bo'lsa (`disable_channel`), sbozor ro'yxatida
                #   ham paydo bo'lmasligi kerak.
                if ch <= 0 or not kanal.get("enabled", True):
                    continue
                nom = str(kanal.get("name") or "").strip() or _NOMSIZ
                # Oqim nomi CamAgent'ning MediaMTX yo'li bilan BIR XIL
                # (`video_routes.py`): sbozor jonli video uchun aynan shu
                # nomga murojaat qiladi.
                oqim = f"cam_{seriya or ip}_{ch}".replace(".", "_").replace("-", "_")
                cur.execute(
                    """
                    INSERT INTO cameras
                        (market_id, nvr_id, channel_no, stream_name, name,
                         status, source_ip, source_model, last_seen_at)
                    VALUES (%s, %s, %s, %s, %s, 'online', %s, %s, now())
                    ON CONFLICT (market_id, nvr_id, channel_no) DO UPDATE SET
                        status       = 'online',
                        source_ip    = EXCLUDED.source_ip,
                        source_model = COALESCE(EXCLUDED.source_model,
                                                cameras.source_model),
                        last_seen_at = now(),
                        updated_at   = now(),
                        -- ⚠ NOM FAQAT QO'LDA O'ZGARTIRILMAGAN BO'LSA
                        --   yangilanadi: operator bergan nom kameradagi
                        --   zavod nomi bilan ustidan yozilmasin.
                        name = CASE WHEN cameras.name_overridden
                                    THEN cameras.name ELSE EXCLUDED.name END
                    """,
                    (market_id, nvr_id, ch, oqim, nom, ip, model),
                )
                yozildi += 1
        return yozildi
