"""Media server (MediaMTX) — jonli video uchun (CLAUDE.md 4-bo'lim, v0.4).

**Nega tayyor server, o'zimiz yozmaymiz.** WebRTC = SDP + ICE + DTLS +
SRTP. Buni Python'da qo'lda yozish bir necha hafta va katta hujum
yuzasi. MediaMTX bitta ikkilik fayl: RTSP qabul qiladi, WebRTC (WHEP)
beradi. CLAUDE.md 11-bo'limida ham aynan shu (yoki go2rtc) nomlangan.

**Oqim yo'li:**

    agent (bozor)  --RTSP push-->  MediaMTX  --WHEP-->  FastAPI proksi
                                   (localhost)          --> brauzer

MediaMTX FAQAT localhost'da tinglaydi. Brauzer unga to'g'ridan-to'g'ri
murojaat qilmaydi — hamma narsa mavjud HTTPS porti orqali, `app.py`
dagi proksi bilan o'tadi. Sabab ikkita:

  1. Yangi ommaviy port ochilmaydi (SBOZOR-CHECKLIST 2B talabi)
  2. Ko'rish huquqi tekshiruvi CHETLAB O'TILMAYDI — MediaMTX'ning o'z
     porti ochiq bo'lsa, havolani bilgan har kim kamerani ko'rardi

Yagona istisno — RTSP qabul porti: agent unga TASHQARIDAN ulanadi.
Bu server tomonidagi port, bozordagi modemda emas, ya'ni 1-prinsip
buzilmaydi (agent baribir o'zi ulanadi).

MediaMTX o'rnatilmagan bo'lsa tizim YIQILMAYDI: `available()` False
qaytaradi va panel "yangilanuvchi rasm" zaxira rejimiga o'tadi.
"""
from __future__ import annotations

import logging
import os
import secrets
import shutil
import socket
import subprocess
import time
from pathlib import Path

log = logging.getLogger("agent_gateway.media")

# Ichki portlar — faqat localhost. Tashqariga chiqmaydi.
DEFAULT_API_PORT = 9997      # MediaMTX boshqaruv API
DEFAULT_WHEP_PORT = 8889     # WebRTC (WHEP) — proksi orqali beriladi
DEFAULT_RTSP_PORT = 8554     # agent RTSP push qiladi (TASHQI)

_CONFIG = """# MediaMTX - CamAgent tomonidan yaratilgan. Qo'lda tahrirlamang.
logLevel: info
logDestinations: [stdout]

# Boshqaruv API va WebRTC - FAQAT localhost. Brauzer bularga
# to'g'ridan-to'g'ri kirmaydi, FastAPI proksi orqali kiradi.
api: yes
apiAddress: 127.0.0.1:{api_port}

webrtc: yes
webrtcAddress: 127.0.0.1:{whep_port}
webrtcLocalUDPAddress: :{udp_port}
# ⛔⛔ TASHQI MANZIL ICE NOMZODI SIFATIDA E'LON QILINADI (260829, jonli
#     serverda o'lchandi).
#
#     Usiz MediaMTX faqat O'ZI ko'rgan manzillarni beradi — Docker
#     tarmog'ida bu `172.x.x.x`, ya'ni brauzer yeta olmaydigan IP.
#     Natijada oqim serverga MUVAFFAQIYATLI kelib turardi (jurnalda
#     `is publishing`), panel «JONLI» deb yozardi, ekran esa QORA
#     qolardi va sabab hech qayerda ko'rinmasdi.
#
# ⚠ UDP PORTI HAM OCHIQ BO'LISHI SHART (`compose.camagent.yml`):
#   nomzod e'lon qilinadi-yu port yopiq bo'lsa natija bir xil — qora
#   ekran.
{additional_hosts}{ice_servers}
# RTSP - agent shu yerga push qiladi. Yagona tashqi port.
#
# `rtspTransports: [tcp]` MUHIM: standart sozlamada MediaMTX RTP/RTCP
# uchun UDP 8000/8001 ni ham band qiladi va u portlar bandligi butun
# serverni ishga tushirmaydi. Agent baribir TCP ishlatadi
# (`streaming.py`: `-rtsp_transport tcp`), ya'ni UDP ortiqcha —
# ortiqcha port esa faqat to'qnashuv manbai.
rtsp: yes
rtspAddress: :{rtsp_port}
rtspTransports: [tcp]

# Ortiqcha protokollar o'chirilgan: hujum yuzasi kichik bo'lsin.
#
# ⛔ `moq:` YOZILMAYDI (260828, jonli serverda o'lchandi). MediaMTX bu
#   maydonni BILMAYDI va noma'lum kalitni ko'rgan zahoti butunlay
#   ishga tushmaydi: «ERR: json: unknown field "moq"». Natijada jonli
#   video umuman ochilmasdi, panel esa faqat «xato» deb ko'rsatardi —
#   sabab MediaMTX jurnalining ichida qolardi.
rtmp: no
hls: no
srt: no

# AUTENTIFIKATSIYA (audit topilmasi). RTSP qabul porti tashqarida
# ochiq. Autentifikatsiyasiz har kim shu portga (a) soxta oqim PUSH
# qilib panelda yolg'on video ko'rsatishi yoki (b) yo'l nomini topib
# kamerani O'QIShi mumkin edi — panel/rol tekshiruvini butunlay chetlab
# o'tib. Endi:
#   * PUSH (publish) — faqat `campub` parolini bilgan agent (parol
#     serverda tasodifiy yaratiladi, publish_url ichida keladi).
#   * READ  — faqat 127.0.0.1 (WHEP proksi) yoki `camread` parolini
#     bilgan servis. Anonim tashqi o'qish taqiqlangan.
#
# ⛔ `camread` NEGA KERAK (260829): sbozor'ning go2rtc'si oqimni SHU
#   serverning ichidan, LEKIN BOSHQA konteynerdan o'qiydi — ya'ni
#   uning manba IP'si `127.0.0.1` emas, Docker tarmog'idagi manzil.
#   Ilgari bunday o'qish jimgina rad etilardi: go2rtc oqimni ro'yxatga
#   olardi, `frame.jpeg` esa NOL BAYT qaytarardi va sabab hech qanday
#   jurnalda ko'rinmasdi.
#
#   Muqobil — butun Docker subnetiga ruxsat berish — RAD ETILDI:
#   o'sha tarmoqda frontend, worker va storage ham turadi va ularning
#   birortasi kamera oqimini o'qishi kerak emas. Parol aniq kimga
#   ruxsat berilganini KO'RSATADI.
authInternalUsers:
  - user: campub
    pass: {pub_secret}
    ips: []
    permissions:
      - action: publish
  - user: camread
    pass: {read_secret}
    ips: []
    permissions:
      - action: read
  - user: any
    pass:
    ips: ['127.0.0.1', '::1']
    permissions:
      - action: read
      - action: playback
      - action: api        # diagnostika (paths/list) — faqat localhost
      - action: metrics

# Publisher uzilishi bilan yo'l o'chadi - "unutilgan" oqim serverda
# qolib ketmasin.
pathDefaults:
  source: publisher
  sourceOnDemand: no
  maxReaders: 10

paths:
  all_others:
"""


class MediaServer:
    """MediaMTX jarayonini boshqaradi. O'rnatilmagan bo'lsa jim turadi."""

    def __init__(self, data_dir: Path, *,
                 api_port: int = DEFAULT_API_PORT,
                 whep_port: int = DEFAULT_WHEP_PORT,
                 rtsp_port: int = DEFAULT_RTSP_PORT,
                 public_host: str = "",
                 turn_url: str = "", turn_user: str = "", turn_pass: str = ""):
        # MUTLAQ yo'l: jarayon `cwd=data_dir` bilan ishga tushadi va
        # nisbiy yo'l ikki marta qo'shilib ketadi
        # (`data/media/data/media/mediamtx.yml`) — fayl topilmaydi.
        self.data_dir = Path(data_dir).resolve()
        self.api_port = api_port
        self.whep_port = whep_port
        self.rtsp_port = rtsp_port
        # Agent shu manzilga push qiladi. Bo'sh bo'lsa jonli video o'chiq.
        self.public_host = public_host or os.environ.get("CAMAGENT_MEDIA_HOST", "")
        # Server ICHIDAN o'qish manzili (sbozor go2rtc'si uchun). Konteyner
        # nomi berilsa RTSP trafigi Docker tarmog'ida qoladi va tashqi
        # interfeysga chiqib qaytmaydi; berilmasa ommaviy manzil ishlatiladi
        # — ishlaydi, lekin bir bozorning oqimi kanalni ikki marta yeydi.
        self.internal_host = os.environ.get("CAMAGENT_MEDIA_INTERNAL_HOST", "")
        self.turn_url = turn_url or os.environ.get("CAMAGENT_TURN_URL", "")
        self.turn_user = turn_user or os.environ.get("CAMAGENT_TURN_USER", "")
        self.turn_pass = turn_pass or os.environ.get("CAMAGENT_TURN_PASS", "")
        self.proc: subprocess.Popen | None = None
        self._binary: str | None = None
        # RTSP publish paroli — tasodifiy, server ishga tushganda yaratiladi
        # va publish_url ichida agentga beriladi. Muhit o'zgaruvchisidan
        # ham olinadi (bir necha server nusxasi bir xil bo'lishi uchun).
        self.pub_secret = (os.environ.get("CAMAGENT_MEDIA_SECRET", "")
                           or secrets.token_urlsafe(24))
        # O'qish paroli — PUBLISH PAROLIDAN BOSHQA. Bir xil bo'lsa
        # o'qiy oladigan har bir servis oqim PUSH ham qila olardi, ya'ni
        # panelda soxta video ko'rsatishi mumkin edi.
        self.read_secret = (os.environ.get("CAMAGENT_MEDIA_READ_SECRET", "")
                            or secrets.token_urlsafe(24))
        # Ishga tushmagan bo'lsa SABABI shu yerda qoladi. Busiz panel
        # faqat "ishga tushmagan" deydi va operator nima bo'lganini
        # bilmaydi (o'lchangan: UDP porti band edi, hech qayerda
        # ko'rinmadi).
        self.last_error: str = ""
        self._log_path = self.data_dir / "mediamtx.log"

    # ------------------------------------------------ mavjudlik

    def binary(self) -> str | None:
        """MediaMTX ikkilik fayli qayerda."""
        if self._binary:
            return self._binary
        nomzodlar = [
            os.environ.get("CAMAGENT_MEDIAMTX", ""),
            str(self.data_dir / "mediamtx.exe"),
            str(self.data_dir / "mediamtx"),
        ]
        for nomzod in nomzodlar:
            if nomzod and Path(nomzod).exists():
                self._binary = nomzod
                return nomzod
        self._binary = shutil.which("mediamtx")
        return self._binary

    def available(self) -> bool:
        """Jonli video umuman mumkinmi.

        Uchtasi ham kerak: ikkilik fayl, ishlayotgan jarayon va agent
        push qiladigan ommaviy manzil. Bittasi yetishmasa panel zaxira
        rejimga (yangilanuvchi rasm) o'tadi — bu xato emas, rejim.
        """
        return bool(self.binary()) and self.running() and bool(self.public_host)

    def running(self) -> bool:
        if self.proc is not None and self.proc.poll() is None:
            return True
        # Boshqa birov ko'targan bo'lishi mumkin (systemd, Docker)
        return self._port_ochiq(self.api_port)

    @staticmethod
    def _port_ochiq(port: int) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            return False

    def sabab(self) -> str:
        """Nega ishlamayapti — panelda ko'rsatish uchun oddiy tilda."""
        if not self.binary():
            return ("MediaMTX o'rnatilmagan. Jonli video o'rniga "
                    "yangilanuvchi rasm ko'rsatiladi.")
        if not self.running():
            if self.last_error:
                return f"MediaMTX ishga tushmadi: {self.last_error}"
            return "MediaMTX ishga tushmagan."
        if not self.public_host:
            return ("Media server manzili sozlanmagan (CAMAGENT_MEDIA_HOST). "
                    "Agent qayerga uzatishni bilmaydi.")
        return ""

    # ------------------------------------------------ hayot tsikli

    def write_config(self) -> Path:
        ice = ""
        if self.turn_url:
            # TURN — to'g'ridan-to'g'ri ulanish ishlamagan holatlar uchun
            # (~10 tadan 2 tasi: simmetrik NAT, korporativ tarmoq).
            ice = ("webrtcICEServers2:\n"
                   f"  - url: {self.turn_url}\n"
                   f"    username: {self.turn_user}\n"
                   f"    password: {self.turn_pass}\n")
        # Tashqi manzil — agent push qiladigan host bilan BIR XIL: brauzer
        # ham o'sha nomga boradi, ya'ni ikkinchi sozlama kerak emas.
        hosts = ""
        if self.public_host:
            hosts = f"webrtcAdditionalHosts: [{self.public_host}]\n"
        matn = _CONFIG.format(api_port=self.api_port, whep_port=self.whep_port,
                              rtsp_port=self.rtsp_port,
                              udp_port=self.whep_port + 100, ice_servers=ice,
                              additional_hosts=hosts,
                              pub_secret=self.pub_secret,
                              read_secret=self.read_secret)
        yol = self.data_dir / "mediamtx.yml"
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(matn, encoding="utf-8")
        return yol

    def start(self) -> tuple[bool, str]:
        if self.running():
            return True, "allaqachon ishlayapti"
        exe = self.binary()
        if not exe:
            return False, self.sabab()
        cfg = self.write_config()
        # Chiqishni FAYLGA yozamiz: `DEVNULL` bo'lsa ishga tushmaslik
        # sababi butunlay yo'qoladi va masofadan tashxis qo'yib bo'lmaydi.
        self._log_path = self.data_dir / "mediamtx.log"
        try:
            log_file = open(self._log_path, "w", encoding="utf-8", errors="replace")
            self.proc = subprocess.Popen(
                [exe, str(cfg)], stdout=log_file, stderr=subprocess.STDOUT,
                cwd=str(self.data_dir))
        except OSError as exc:
            self.last_error = str(exc)
            return False, f"MediaMTX ishga tushmadi: {exc}"
        for _ in range(50):                      # 5 soniyagacha kutamiz
            if self._port_ochiq(self.api_port):
                log.info("MediaMTX ishga tushdi (RTSP :%d, WHEP :%d)",
                         self.rtsp_port, self.whep_port)
                return True, "ishga tushdi"
            if self.proc.poll() is not None:
                self.last_error = self._read_error()
                log.error("MediaMTX yiqildi: %s", self.last_error)
                return False, f"MediaMTX yiqildi: {self.last_error}"
            time.sleep(0.1)
        self.last_error = "javob bermadi (20 s)"
        return False, "MediaMTX javob bermadi"

    def _read_error(self) -> str:
        """MediaMTX jurnalidan xato satrini oladi."""
        try:
            satrlar = self._log_path.read_text(encoding="utf-8",
                                               errors="replace").splitlines()
        except OSError:
            return f"chiqish kodi {self.proc.returncode if self.proc else '?'}"
        for satr in reversed(satrlar):
            if " ERR " in satr:
                return satr.split(" ERR ", 1)[1].strip()[:200]
        return (satrlar[-1][:200] if satrlar
                else f"chiqish kodi {self.proc.returncode if self.proc else '?'}")

    def stop(self) -> None:
        if self.proc is None or self.proc.poll() is not None:
            return
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        log.info("MediaMTX to'xtatildi")

    # ------------------------------------------------ manzillar

    @staticmethod
    def path_for(agent_id: str, channel: int, nvr_serial: str = "") -> str:
        """Oqim yo'li. Faqat harf/raqam — MediaMTX yo'l nomi qat'iy va bu
        qiymat URL'ga tushadi, ya'ni tozalanmasa yo'l chiqishi mumkin.

        ⛔⛔ SERIYA YO'LNING BIR QISMI (260829, Karmanada o'lchandi).

            NVR'siz obyektda har kamera ALOHIDA qurilma va ularning
            HAMMASIDA kanal = 1 (7-bo'lim). Seriyasiz yo'l 16 kamerani
            bitta `agentid_1` ga yig'ardi: devorda ikkinchi kamerani
            ochgan operator BIRINCHISINING tasvirini ko'rar va buni
            «kamera noto'g'ri ulangan» deb hisoblardi. Nizoda esa bu
            dalilni butunlay yaroqsiz qilardi — kadr ostidagi nom
            boshqa kameraniki bo'lardi.

            Eski (seriyasiz) chaqiruv ATAYIN saqlanadi: NVR'li obyektda
            kanal raqami o'zi yagona va yo'l nomini uzaytirish MediaMTX
            konfiguratsiyasidagi mavjud yo'llarni buzardi.
        """
        toza = "".join(c for c in str(agent_id).lower() if c.isalnum())
        if not nvr_serial:
            return f"{toza}_{int(channel)}"
        seriya = "".join(c for c in str(nvr_serial).lower() if c.isalnum())
        return f"{toza}_{seriya}_{int(channel)}"

    def publish_url(self, agent_id: str, channel: int,
                    nvr_serial: str = "") -> str:
        """Agent shu manzilga uzatadi (`start_stream` parametri).

        Publish paroli URL ichida — faqat shu parolni bilgan agent oqim
        yubora oladi. Parol tasodifiy, ffmpeg jurnalida niqoblanadi.
        """
        return (f"rtsp://campub:{self.pub_secret}@{self.public_host}:"
                f"{self.rtsp_port}/"
                f"{self.path_for(agent_id, channel, nvr_serial)}")

    def read_url(self, agent_id: str, channel: int,
                 nvr_serial: str = "") -> str:
        """Oqimni O'QISH manzili — sbozor go2rtc'si shu yerdan oladi.

        ⚠ PAROL O'QISH UCHUN, PUBLISH UCHUN EMAS (`camread`). 8554
          porti internetdan ochiq — anonim o'qish yo'l nomini topgan
          har kimga kamerani ochib berardi. Publish paroli esa BOSHQA:
          o'qiy oladigan servis oqim yubora olmaydi.
        """
        host = self.internal_host or self.public_host
        return (f"rtsp://camread:{self.read_secret}@{host}:{self.rtsp_port}/"
                f"{self.path_for(agent_id, channel, nvr_serial)}")

    def path_ready(self, path: str) -> bool:
        """Yo'lda oqim BORmi (MediaMTX API).

        `ready: false` — yo'l e'lon qilingan, lekin kadr kelmagan;
        o'quvchi bunday yo'lga ulanolmaydi.
        """
        import json
        import urllib.request

        try:
            manzil = f"http://127.0.0.1:{self.api_port}/v3/paths/get/{path}"
            with urllib.request.urlopen(manzil, timeout=2) as javob:
                return bool(json.load(javob).get("ready"))
        except Exception:                              # noqa: BLE001
            return False

    def wait_ready(self, agent_id: str, channel: int, nvr_serial: str = "",
                   timeout_s: float = 12.0) -> bool:
        """Oqim paydo bo'lguncha kutadi.

        ⛔⛔ NEGA KUTISH SHART (260829, jonli sinovda o'lchandi).

            Zanjir: gateway agentga buyruq yuboradi -> agent ffmpeg'ni
            ko'taradi -> ffmpeg kameradan o'qib MediaMTX'ga uzatadi.
            Bu ~2-4 soniya. Gateway darrov javob bersa, sbozor o'sha
            zahoti go2rtc'ga «shu manzildan o'qi» deydi va go2rtc BO'SH
            yo'lga ulanib **400** oladi.

            O'lchangan hodisa: go2rtc 07:08:01 da ulandi, agent 07:08:03
            da publish qildi — ikki soniya farq va ekran QORA qoldi.
            Foydalanuvchi uchun bu «ba'zan ishlaydi, ba'zan yo'q» bo'lib
            ko'rinardi, ya'ni eng yomon turdagi nosozlik.

        ⚠ KUTISH TUGASA HAM `False` QAYTARILADI, ISTISNO EMAS:
          chaqiruvchi baribir seansni ochgan va agentga buyruq
          yuborilgan — oqim keyinroq kelishi mumkin va operatorning
          «Qayta urinish» bosishi ishlaydi.
        """
        yol = self.path_for(agent_id, channel, nvr_serial)
        oxiri = time.time() + timeout_s
        while time.time() < oxiri:
            if self.path_ready(yol):
                return True
            time.sleep(0.4)
        log.warning("oqim %s belgilangan vaqtda tayyor bo'lmadi", yol)
        return False

    def whep_url(self, agent_id: str, channel: int,
                 nvr_serial: str = "") -> str:
        """Ichki WHEP manzili — proksi shu yerdan oladi."""
        return (f"http://127.0.0.1:{self.whep_port}/"
                f"{self.path_for(agent_id, channel, nvr_serial)}/whep")
