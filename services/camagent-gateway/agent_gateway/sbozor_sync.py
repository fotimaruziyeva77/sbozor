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
        # Kadr xabari uchun — BAZA EMAS, HTTP. Sabab: `snapshots` yozuvi
        # sifat tahlilini talab qiladi va u core-api'da (`quality.py`).
        self.api_url = os.environ.get("CAMAGENT_SBOZOR_API", "")
        self.api_token = os.environ.get("CAMAGENT_SBOZOR_TOKEN", "")
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


    def touch_cameras(self, key_prefix: str) -> int:
        """Bozor kameralarining `last_seen_at` ini yangilaydi.

        ⛔⛔ NEGA KERAK (260829, panelda o'lchandi). sbozor `cameras.status`
            ni AGENT AYTGAN paytdagi holatda saqlaydi va uni hech kim
            eskirtirmaydi. Agent to'xtaganda — xizmat yiqilsa, bozor
            internetdan uzilsa — panel «16 ta kamera Onlayn» deb
            ko'rsataverardi. Yonida esa «oxirgi ko'rilgan: 1 soat oldin»
            yozuvi turardi: ikkita qarama-qarshi fakt bir qatorda.

            Nizoda bu qimmat: operator kameralar ishlayapti deb hisoblab,
            keyin o'sha soatlar uchun kadr yo'qligini ko'radi.

        ⚠ SIGNAL — HEARTBEAT, KADR EMAS. Kadr soatiga bir marta keladi,
          heartbeat esa har 60 soniyada: faqat kadrga tayanish uzilishni
          bir soatgacha yashirardi.

        ⚠ FAQAT `camagent` QURILMALARI: sbozor o'zi ulanadigan NVR'ning
          holatini o'z kashfiyoti bilan biladi va bu yerdagi yangilash
          uni buzardi.
        """
        market_id = market_id_from_prefix(key_prefix)
        if not (self.enabled and market_id):
            return 0
        try:
            with self._psycopg.connect(self.dsn, autocommit=True) as conn,                     conn.cursor() as cur:
                cur.execute("""
                    UPDATE cameras c
                       SET last_seen_at = now(), updated_at = now()
                      FROM nvr_devices d
                     WHERE d.market_id = c.market_id AND d.id = c.nvr_id
                       AND d.username = 'camagent'
                       AND c.market_id = %s
                       AND c.is_archived = false
                """, (market_id,))
                return cur.rowcount or 0
        except Exception as exc:                      # noqa: BLE001
            log.warning("sbozor kamera vaqtini yangilab bo'lmadi: %s", exc)
            return 0

    # ------------------------------------------------ kadrlar

    def notify_snapshot(self, key_prefix: str, meta: dict, ref: str,
                        size_bytes: int) -> bool:
        """Kadr S3'ga yozilgach sbozor'ga xabar beradi.

        ⛔⛔ SIFAT VERDIKTI BU YERDA HISOBLANMAYDI. `snapshots.is_billable`
            verdiktdan GENERATED ustun sifatida chiqadi — ya'ni baho PUL
            qaroriga bevosita ta'sir qiladi. Chegaralar va ularning
            versiyasi sbozor tomonida yashaydi; gateway o'z verdiktini
            yuborsa ikkita chegara to'plami paydo bo'lardi va ular
            jimgina ajralib ketardi.

            Shuning uchun bu yerda faqat FAKT: kadr qayerda, qachon,
            qaysi kameradan. Baho — core-api'da.

        ⚠ XATO YUTILADI: sbozor javob bermasa ham kadr S3'da va gateway
          bazasida QOLADI (4-prinsip). Keyingi kadr yana urinadi.
        """
        market_id = market_id_from_prefix(key_prefix)
        if not (self.api_url and self.api_token and market_id):
            return False
        seriya = str(meta.get("nvr_serial") or "")
        kanal = int(meta.get("channel") or 0)
        if not seriya or kanal <= 0:
            return False

        vaqt = _iso(meta.get("agent_time")) or _hozir()
        slot = _slot_from_meta(meta, vaqt)
        try:
            import json
            import urllib.request

            tana = json.dumps({
                "market_id": market_id,
                "camera_serial": seriya,
                "channel_no": kanal,
                "object_key": _s3_key(ref),
                "size_bytes": int(size_bytes),
                "captured_at": vaqt,
                "slot_time": slot,
                # Jadval sloti bo'lmasa (qo'lda buyruq) kadr o'z vaqtiga
                # rejalashtirilgan deb yoziladi — sbozor uni «kech» deb
                # belgilamasin.
                "scheduled_at": vaqt,
                "late": bool(meta.get("late")),
            }).encode()
            req = urllib.request.Request(
                f"{self.api_url.rstrip('/')}/internal/camagent/snapshot",
                data=tana, method="POST",
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {self.api_token}"})
            with urllib.request.urlopen(req, timeout=15) as javob:
                return javob.status == 200
        except Exception as exc:                  # noqa: BLE001
            log.warning("sbozor kadr xabari yiqildi: %s", exc)
            return False



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


def _s3_key(ref: str) -> str:
    """`s3://bucket/kalit` -> `kalit`. Disk rejimida ref o'zi kalit."""
    if ref.startswith("s3://"):
        qism = ref[5:].split("/", 1)
        return qism[1] if len(qism) == 2 else qism[0]
    return ref


def _iso(qiymat: object) -> str:
    return str(qiymat) if qiymat else ""


def _hozir() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _slot_from_meta(meta: dict, vaqt: str) -> str:
    """Jadval sloti — kadr metadatasidan yoki olingan vaqtdan.

    Agent slot vaqtini `trigger` da beradi (`slot:06:00`); qo'lda
    buyruqda (`command:...`) slot yo'q va o'shanda kadr olingan soat
    ishlatiladi.
    """
    trigger = str(meta.get("trigger") or "")
    if trigger.startswith("slot:"):
        return trigger[5:][:5]
    # ⛔ SLOT YO'Q -> BO'SH QATOR, UTC SOATI EMAS (260829).
    #   Gateway UTC'da ishlaydi va bozor mintaqasini BILMAYDI. Ilgari
    #   bu yerda `vaqt[11:16]` qaytarilardi: Karmanada 06:18 da qo'lda
    #   olingan kadr sbozor jadvalida `01:18` ustuni bo'lib chiqdi va
    #   operator uni tanimadi. Bo'sh qator core-api'ga «slotni O'ZING
    #   hisobla» deydi — u bozor mintaqasini biladi.
    return ""

    # ------------------------------------------------ qurilmalar
