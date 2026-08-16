"""ZAXIRA ZANJIRINING STATIK DARVOZASI (FOUND-07, 08-05).

=============================================================================
NEGA BU DARVOZA BOR.

`ops/backup/` — shell va SQL, ya'ni na `mypy`, na `ruff`, na birorta
birlik testi unga qaramaydi. Undagi TO'RTTA xato JIMGINA o'tib ketardi va
har biri «zaxira olinyapti» degan YOLG'ON ishonch berardi:

  1. `pg_dump | restic backup --stdin` — POSIX quvurida OXIRGI buyruqning
     chiqish kodi qaytadi, ya'ni yiqilgan dump MUVAFFAQIYAT deb yozilardi;
  2. `--compress=0` siz `--format=custom` zlib bilan siqadi va restic'ning
     deduplikatsiyasi butunlay o'ladi (14 kunlik retention = 14 x baza);
  3. yurak urishi zanjirning O'RTASIDA yoki `trap EXIT` ichida yozilsa,
     u NOSOZLIKDA HAM yozilardi va `backup_stale` MANGU jim qolardi;
  4. `heartbeat.sql` dagi komponent nomi `alerting.BACKUP_COMPONENT` dan
     ajralsa, zaxira ishlab turgan holda `/internal/self-check` uni mangu
     `never_seen` da ko'rsatardi.

Uchalasining ham nosozlik SHAKLI bir xil: hech nima qizarmaydi.

=============================================================================
SKANERNING IKKI QOIDASI (`test_compose_sim_env.py` dan meros).

1. **QUYI CHEGARA MAJBURIY** (`MIN_SCANNED_FILES`). Yo'l noto'g'ri
   yozilganda yoki `ops/backup/` ko'chirilganda skaner BO'SH to'plamda
   ishlab, hamma assert jimgina o'tib ketardi.

   ⚠ SHAKL FARQI VA U ATAYIN: bu yerda quyi chegara ALOHIDA TEST emas,
     `autouse` FIXTURE — ya'ni u ETTALA o'lchovning HAR BIRIDAN oldin
     bajariladi. Alohida test bo'lganda u yolg'iz o'zi qizarib, qolgan
     yetti da'vo bo'sh-rost holida «yashil» bo'lib turardi; fixture esa
     ularning hech biriga ishlashga imkon bermaydi.

2. **SKANER O'Z FAYLINI SKANLANADIGAN TO'PLAMDAN CHIQARIB TASHLAYDI.**
   Bu yerda sabab MAXSUS va u nazariy emas: pastda `_PIPE_CONTROL`
   konstantasi bor va u AYNAN taqiqlangan matnni (`pg_dump | restic`)
   tashiydi — u nazorat namunasi sifatida kerak. Bu fayl skanlanadigan
   to'plamga tushsa 3-o'lchov YOLG'ON-QIZIL bo'lardi.
=============================================================================
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

import pytest
from app.jobs import alerting

REPO_ROOT: Final = Path(__file__).resolve().parents[2]
BACKUP_DIR: Final = REPO_ROOT / "ops" / "backup"
RUN_BACKUP: Final = BACKUP_DIR / "run-backup.sh"
LOOP: Final = BACKUP_DIR / "loop.sh"
HEARTBEAT: Final = BACKUP_DIR / "heartbeat.sql"
COMPOSE: Final = REPO_ROOT / "compose.yaml"
ENV_EXAMPLE: Final = REPO_ROOT / ".env.example"

MIN_SCANNED_FILES: Final = 5
"""Quyi chegara — 1-qoida.

`ops/backup/` bugun AYNAN beshta fayl: `Dockerfile`, `run-backup.sh`,
`loop.sh`, `heartbeat.sql`, `README.md`. Bu PASTKI chegara: fayl
qo'shilsa u qayta ko'rib chiqilmaydi, fayl YO'QOLSA esa darhol qizaradi.
"""

REQUIRED_FILES: Final = (RUN_BACKUP, LOOP, HEARTBEAT, COMPOSE, ENV_EXAMPLE)

ENV_KEYS: Final = (
    "BACKUP_DATABASE_URL",
    "RESTIC_REPOSITORY",
    "RESTIC_PASSWORD",
    "BACKUP_S3_ACCESS_KEY",
    "BACKUP_S3_SECRET_KEY",
)

RETENTION: Final = "--keep-daily 14 --keep-weekly 8 --keep-monthly 12"
"""C-3 — qiymatlar CLAUDE.md § Backups va D-12 dan, LITERAL qulflangan.

Ular «tavsiya» emas, SIYOSAT: 14 kunlik kunlik nusxa nizoning tipik
aniqlanish oynasi, 12 oylik esa moliyaviy yilning yopilishi. O'zgarishi
ONGLI qaror bo'lishi kerak, yo'l-yo'lakay tahrir emas.
"""

_PIPE_RE: Final = re.compile(r"(?<!\|)\|(?!\|)")
"""YAKKA `|` — ya'ni QUVUR. `||` (mantiqiy YOKI) ATAYIN chetlab o'tiladi.

`restic cat config >/dev/null 2>&1 || restic init` — qonuniy shakl va u
bu naqshga tushmasligi shart, aks holda darvoza yolg'on-qizil bo'lardi.
"""

_PIPE_CONTROL: Final = 'pg_dump --dbname="$X" | restic backup --stdin'
"""⛔ NAZORAT NAMUNASI — predikatning O'ZI ishlayotganini o'lchaydi.

Usiz 3-o'lchov «hech qanday quvur topilmadi» deb MANGU yashil bo'lardi,
hatto `_PIPE_RE` buzilgan bo'lsa ham. Aynan shu satr tufayli bu fayl
skanlanadigan to'plamdan chiqarib tashlanadi (fayl docstringi, 2-qoida).
"""

_HEARTBEAT_VALUES_RE: Final = re.compile(r"VALUES\s*\(\s*'([^']*)'", re.IGNORECASE)
_LOOP_COMPONENT_RE: Final = re.compile(r"component\s*=\s*'([^']*)'")
_ENV_ENTRY_RE: Final = re.compile(r"^ {6}([A-Z][A-Z0-9_]*):\s*(\S.*)$")
_SECRET_KEY_RE: Final = re.compile(r"^(RESTIC_|AWS_|BACKUP_)")


# ---------------------------------------------------------------------------
# YIG'UVCHILAR
# ---------------------------------------------------------------------------


def _scanned() -> dict[Path, str]:
    """Skanlanadigan fayllar — SHU FAYLNING O'ZIDAN TASHQARI (2-qoida)."""
    own = Path(__file__).resolve()
    found: dict[Path, str] = {}
    for path in sorted(BACKUP_DIR.glob("*")):
        if path.is_file() and path.resolve() != own:
            found[path] = path.read_text(encoding="utf-8")
    for path in (COMPOSE, ENV_EXAMPLE):
        if path.is_file() and path.resolve() != own:
            found[path] = path.read_text(encoding="utf-8")
    return found


SCANNED: Final = _scanned()


def _code_lines(text: str, comment: str) -> list[str]:
    """Bo'sh qatorlar va BUTUN-QATOR izohlar tashlanadi.

    ⚠ Qator OXIRIDAGI izoh QOLDIRILADI (`test_compose_sim_env.py` bilan
      bir xil qaror): uni kesish `#` ni satr ichida izlashni talab
      qilardi va u qiymat ichidagi `#` ni ham kesib yuborardi. Shu
      sababdan `ops/backup/*.sh` da qator oxirida izoh YOZILMAYDI.
    """
    return [
        line for line in text.splitlines() if line.strip() and not line.lstrip().startswith(comment)
    ]


def _logical_commands(text: str, comment: str = "#") -> list[str]:
    """`\\` bilan bo'lingan qatorlar BITTA mantiqiy buyruqqa yig'iladi.

    ⛔ MAJBURIY: `restic backup --stdin-from-command … -- pg_dump …`
      chaqirig'i BESH qatorga yoyilgan. Qator-qator o'qiydigan skaner
      `pg_dump` va `restic` ni BOSHQA-BOSHQA buyruq deb ko'rardi va
      «orasida quvur bormi?» degan savolning O'ZI ma'nosiz bo'lardi.
    """
    commands: list[str] = []
    buffer = ""
    for line in _code_lines(text, comment):
        stripped = line.rstrip()
        if stripped.endswith("\\"):
            buffer += stripped[:-1].strip() + " "
            continue
        commands.append((buffer + stripped.strip()).strip())
        buffer = ""
    if buffer:
        commands.append(buffer.strip())
    return commands


def _compose_block(name: str) -> list[str]:
    """`compose.yaml` dagi bitta xizmat blokining qatorlari."""
    lines = COMPOSE.read_text(encoding="utf-8").splitlines()
    start: int | None = None
    for index, line in enumerate(lines):
        if line == f"  {name}:":
            start = index
            break
    if start is None:
        return []
    block: list[str] = []
    for line in lines[start + 1 :]:
        if line.strip() and not line.startswith("    "):
            break
        block.append(line)
    return block


@pytest.fixture(autouse=True)
def _scanner_saw_the_files() -> None:
    """QUYI CHEGARA — HAR o'lchovdan oldin (fayl docstringi, 1-qoida)."""
    assert len(SCANNED) >= MIN_SCANNED_FILES, (
        f"skaner atigi {len(SCANNED)} fayl ko'rdi (kutilgan >= "
        f"{MIN_SCANNED_FILES}) — `{BACKUP_DIR}` ko'chirilgan yoki yo'l "
        "eskirgan bo'lsa quyidagi da'volarning hammasi bo'sh-rost bo'lardi"
    )
    missing = [path.name for path in REQUIRED_FILES if path not in SCANNED]
    assert not missing, f"skanlanadigan to'plamda yo'q fayl(lar): {missing}"


# ---------------------------------------------------------------------------
# (a) Komponent nomi mahsulot konstantasi bilan bir xil
# ---------------------------------------------------------------------------


def test_heartbeat_component_matches_the_alerting_constant() -> None:
    """`heartbeat.sql` VA `loop.sh` dagi nom `BACKUP_COMPONENT` ga TENG.

    ⛔ KUTILGAN QIYMAT SHU YERDA LITERAL YOZILMAYDI — u mahsulotdan
       IMPORT qilinadi. Qayta yozilgan literal ikki nusxani tug'dirardi
       va nom o'zgarganda darvoza O'ZI bilan birga eskirardi.

    ⚠ `loop.sh` HAM tekshiriladi (rejadan tashqari, Rule 2): u
      `already_done_today()` ichida o'sha nomni IKKINCHI marta yozadi.
      Ajralib ketsa tsikl kunlik yozuvni HECH QACHON topmasdi va HAR 10
      DAQIQADA to'liq zaxira boshlanardi — offsite trafik va `--prune`
      takror-takror, hech qanday xatosiz.
    """
    expected = alerting.BACKUP_COMPONENT
    sql = SCANNED[HEARTBEAT]

    sql_names = _HEARTBEAT_VALUES_RE.findall(sql)
    assert sql_names, (
        f"`{HEARTBEAT.name}` da `VALUES ('<komponent>', …)` shakli topilmadi — "
        "so'rov qayta yozilgan bo'lsa bu darvoza ham yangilanishi kerak"
    )
    assert sql_names[0] == expected, (
        f"komponent nomi AJRALIB KETDI: `{HEARTBEAT.name}` da "
        f"'{sql_names[0]}', `alerting.BACKUP_COMPONENT` esa '{expected}'. "
        "Zaxira ishlab tursa ham `/internal/self-check` uni MANGU "
        "`never_seen` da ko'rsatardi va `alert_sweep` har kuni CRITICAL "
        "alert yozardi."
    )
    assert sql.count(f"'{sql_names[0]}'") == 1, (
        f"`{HEARTBEAT.name}` da '{sql_names[0]}' satri BIR MARTADAN KO'P "
        "uchraydi — komponent nomi aynan bitta joyda yozilishi shart"
    )

    loop_names = _LOOP_COMPONENT_RE.findall(SCANNED[LOOP])
    assert loop_names, (
        f"`{LOOP.name}` da `component = '<nom>'` sharti topilmadi — "
        "`already_done_today()` so'rovi o'zgargan bo'lsa darvoza ham o'zgaradi"
    )
    drifted = sorted({name for name in loop_names if name != expected})
    assert not drifted, (
        f"`{LOOP.name}` dagi komponent nomi AJRALIB KETDI: {drifted}, "
        f"`alerting.BACKUP_COMPONENT` esa '{expected}'. Tsikl kunlik "
        "yozuvni topmasdi va har 10 daqiqada to'liq zaxira boshlanardi."
    )


# ---------------------------------------------------------------------------
# (b) Retention qiymatlari LITERAL qulflangan (C-3)
# ---------------------------------------------------------------------------


def test_retention_values_are_locked() -> None:
    """`--keep-daily 14 --keep-weekly 8 --keep-monthly 12 --prune` — AYNAN.

    Qiymatlar CLAUDE.md § Backups va D-12 dan. Ular jimgina o'zgarsa
    natija ikki tomonlama yomon: kichrayganda tiklash oynasi qisqaradi
    (buni faqat kerak bo'lganda bilinadi), kattalashganda offsite hisobi
    va Contabo diski o'sadi.
    """
    forget = [cmd for cmd in _logical_commands(SCANNED[RUN_BACKUP]) if "restic forget" in cmd]
    assert len(forget) == 1, (
        f"`{RUN_BACKUP.name}` da `restic forget` chaqirig'i aynan bitta "
        f"bo'lishi kutilgan, topilgani: {forget}"
    )
    assert RETENTION in forget[0], (
        f"retention qiymatlari o'zgargan: `{forget[0]}`.\nKutilgan literal: "
        f"`{RETENTION}` (CLAUDE.md § Backups, D-12). O'zgarish ONGLI qaror "
        "bo'lishi kerak — shu satr bilan birga sabab ham yozilsin."
    )
    assert "--prune" in forget[0], (
        "`--prune` YO'Q: `forget` snapshotni reyestrdan chiqaradi, lekin "
        "ma'lumot bloklari repoda QOLADI va offsite hajmi hech qachon "
        "kichraymasdi"
    )


# ---------------------------------------------------------------------------
# (c) Dump QUVUR BILAN uzatilmaydi (Pitfall 5)
# ---------------------------------------------------------------------------


def test_dump_is_not_piped_into_restic() -> None:
    """`pg_dump` va `restic` orasida QUVUR YO'Q, `--stdin-from-command` BOR.

    ⛔ SABAB: POSIX quvurida OXIRGI buyruqning chiqish kodi qaytadi.
       `pg_dump` yiqilganda (parol xato, disk to'la, ulanish uzildi)
       restic BO'SH yoki QISQARTIRILGAN oqimni muvaffaqiyat bilan
       yozardi, tsikl yurak urishini yozardi va `backup_stale` MANGU jim
       turardi — FOUND-07 ning butun kafolati soxta bo'lardi.
    """
    assert _PIPE_RE.search(_PIPE_CONTROL), (
        "⛔ NAZORAT YIQILDI: `_PIPE_RE` taqiqlangan namunadagi quvurni "
        f"KO'RMADI (`{_PIPE_CONTROL}`). Predikat buzilgan, ya'ni quyidagi "
        "da'vo bo'sh-rost bo'lardi."
    )
    assert not _PIPE_RE.search("restic cat config >/dev/null 2>&1 || restic init"), (
        "⛔ NAZORATNING IKKINCHI YARMI YIQILDI: `_PIPE_RE` mantiqiy `||` ni "
        "quvur deb o'qidi — darvoza yolg'on-qizil bo'lardi"
    )

    commands = _logical_commands(SCANNED[RUN_BACKUP])
    assert any("--stdin-from-command" in cmd for cmd in commands), (
        f"`{RUN_BACKUP.name}` da `--stdin-from-command` YO'Q. Faqat u "
        "`pg_dump` ning CHIQISH KODINI tekshiradi (rasmiy hujjat: «A "
        "non-zero exit code from the command causes restic to cancel the "
        "backup»)."
    )

    piped = [
        cmd for cmd in commands if _PIPE_RE.search(cmd) and ("pg_dump" in cmd or "restic" in cmd)
    ]
    assert not piped, (
        f"`{RUN_BACKUP.name}` da QUVUR topildi: {piped}\n\n"
        "Quvurda `pg_dump` ning nosozligi YUTILADI va yiqilgan dump "
        "MUVAFFAQIYAT deb yoziladi. To'g'ri shakl — `restic backup "
        "--stdin-from-command … -- pg_dump …`."
    )


# ---------------------------------------------------------------------------
# (d) Dump SIQILMAGAN holda uzatiladi (Pitfall 6)
# ---------------------------------------------------------------------------


def test_dump_is_uncompressed() -> None:
    """`pg_dump` chaqirig'ida `--compress=0` (yoki `-Z0`) BOR.

    ⛔ SABAB: `--format=custom` standart holatda zlib bilan siqadi.
       Siqilgan oqimda BITTA baytning o'zgarishi undan keyingi BARCHA
       baytlarni o'zgartiradi, ya'ni restic har kuni butun bazani YANGI
       ma'lumot deb saqlardi — 14 kunlik retention 14 x to'liq baza.
       Siqishni restic O'ZI qiladi (`--compression auto`, standart).
    """
    dumps = [cmd for cmd in _logical_commands(SCANNED[RUN_BACKUP]) if "pg_dump" in cmd]
    assert len(dumps) == 1, (
        f"`{RUN_BACKUP.name}` da `pg_dump` chaqirig'i aynan bitta bo'lishi "
        f"kutilgan, topilgani: {dumps}"
    )
    assert "--compress=0" in dumps[0] or "-Z0" in dumps[0], (
        f"`pg_dump` SIQISH BILAN chaqirilyapti: `{dumps[0]}`\n\n"
        "`--compress=0` (yoki `-Z0`) MAJBURIY — usiz restic'ning "
        "deduplikatsiyasi butunlay o'ladi va offsite hajmi har kuni "
        "to'liq baza hajmiga o'sadi."
    )


# ---------------------------------------------------------------------------
# (e) Yurak urishi FAQAT to'liq muvaffaqiyatdan keyin (Pattern 4, D-15)
# ---------------------------------------------------------------------------


def test_heartbeat_is_written_only_after_full_success() -> None:
    """Yurak urishi — OXIRGI qadam, `trap` da emas, sozlanmaganda YO'Q.

    ⛔ UCH DA'VO BIR MAVZUNING UCH YARMI: qator faqat va faqat butun
       zanjir muvaffaqiyat bilan tugaganda yoziladi.

    ⚠ SHAKL: reja bu o'lchovni (e) deb ataydi va `loop.sh` ning
      `backup_unconfigured` shoxini alohida bandda so'raydi. Ular shu
      yerda BIRGA o'lchanadi, chunki ikkalasi ham AYNAN BIR XIL da'voni
      himoya qiladi — «yurak urishi muvaffaqiyat SIGNALI, tiriklik
      signali EMAS» (D-15). Sanoq shu sababdan yettita bo'lib qoladi.
    """
    commands = _logical_commands(SCANNED[RUN_BACKUP])
    beats = [index for index, cmd in enumerate(commands) if "heartbeat.sql" in cmd]
    assert len(beats) == 1, (
        f"`{RUN_BACKUP.name}` da `heartbeat.sql` chaqirig'i aynan bitta "
        f"bo'lishi kutilgan, topilgani: {beats}"
    )

    tail = commands[beats[0] + 1 :]
    offenders = [cmd for cmd in tail if "restic" in cmd or "pg_dump" in cmd]
    assert not offenders, (
        f"yurak urishidan KEYIN yana zaxira qadami bor: {offenders}\n\n"
        "⛔ Qator zanjirning ENG OXIRIDA yozilishi shart: `set -e` undan "
        "keyingi nosozlikni to'xtata olmaydi, ya'ni yiqilgan yugurish "
        "«muvaffaqiyat» deb belgilangan bo'lib qolardi va `backup_stale` "
        "hech qachon ko'tarilmasdi (D-15)."
    )
    assert beats[0] == len(commands) - 1, (
        f"yurak urishi oxirgi buyruq EMAS (o'rni {beats[0] + 1}/{len(commands)})"
    )

    traps = [cmd for cmd in commands if cmd.startswith("trap ")]
    assert not traps, (
        f"`{RUN_BACKUP.name}` da `trap` topildi: {traps}\n\n"
        "⛔ `trap … EXIT` ichida yozilgan yurak urishi NOSOZLIKDA HAM "
        "yozilardi — tizim o'zining ishlamayotganini «muvaffaqiyat» deb "
        "belgilardi."
    )

    loop_commands = _logical_commands(SCANNED[LOOP])
    assert any("backup_unconfigured" in cmd for cmd in loop_commands), (
        f"`{LOOP.name}` da `backup_unconfigured` shoxi YO'Q — sirlari "
        "to'ldirilmagan konteyner jim ishlab, nosozlik faqat falokat kuni "
        "bilinardi"
    )
    exits = [cmd for cmd in loop_commands if re.search(r"(^|[;&|]\s*)exit\b(?!=)", cmd)]
    assert not exits, (
        f"`{LOOP.name}` da `exit` topildi: {exits}\n\n"
        "⛔ `restart: unless-stopped` bilan chiqish CRASH-LOOP bo'lardi va "
        "dev muhitida `npm run up` jurnalini ifloslantirardi. Sozlanmagan "
        "tsikl uxlaydi, xabar yozadi va yurak urishini YOZMAYDI."
    )


# ---------------------------------------------------------------------------
# (f) Compose bloki: sir literal emas, `:ro` bor, profil yo'q
# ---------------------------------------------------------------------------


def test_compose_backup_block_keeps_secrets_out_and_archive_readonly() -> None:
    """`backup` bloki: `${...}`, `seaweed:/seaweed:ro`, PROFILSIZ.

    Uch da'vo, uchtasi ham xavf reyestridan: T-08-18 (sir compose'da
    literal emas), T-08-19 (zaxira jarayoni arxivni qayta yoza olmaydi)
    va D-13 (profil ortida qolgan zaxira hech qachon olinmaydi).
    """
    block = _compose_block("backup")
    assert block, "`compose.yaml` da `backup:` bloki topilmadi"

    assert any("dockerfile: ops/backup/Dockerfile" in line for line in block), (
        "`backup` bloki `ops/backup/Dockerfile` ni qurmayapti — build "
        "manbai ko'chgan bo'lsa u yerdagi izohlar ham ko'chishi kerak"
    )

    code = _code_lines("\n".join(block), "#")
    literals: list[str] = []
    for line in code:
        match = _ENV_ENTRY_RE.match(line)
        if match is None:
            continue
        key, value = match.group(1), match.group(2).strip()
        if _SECRET_KEY_RE.match(key) and not value.startswith("${"):
            literals.append(f"{key}: {value}")
    assert not literals, (
        f"`backup` blokida LITERAL qiymat(lar): {literals}\n\n"
        "⛔ Sirlar `compose.yaml` da hech qachon literal yozilmaydi — u "
        "git'da, `.env` esa emas (T-08-18)."
    )

    assert any("seaweed:/seaweed:ro" in line for line in code), (
        "`backup` blokida `seaweed:/seaweed:ro` mount YO'Q. `:ro` siz "
        "zaxira jarayoni butun dalil arxivini QAYTA YOZA olardi — ya'ni "
        "bitta xato buyruq aynan himoya qilinayotgan narsani yo'q qilardi "
        "(T-08-19)."
    )
    assert not any(line.strip().startswith("profiles:") for line in code), (
        "`backup` bloki PROFIL ortiga qo'yilgan — profilsiz `docker "
        "compose up` uni umuman ko'rmasdi va zaxira HECH QACHON olinmasdi "
        "(D-13)"
    )


# ---------------------------------------------------------------------------
# (g) `.env.example` beshala kalitni e'lon qiladi
# ---------------------------------------------------------------------------


def test_env_example_declares_the_five_backup_keys() -> None:
    """Besh kalit NAMUNA faylda — aks holda ular faqat kodda yashardi.

    `cp .env.example .env` qilgan yangi o'rnatmada e'lon qilinmagan kalit
    JIMGINA bo'sh qolardi va konteyner `backup_unconfigured` holatida
    mangu turardi — nosozlik bor, lekin uni tuzatish uchun kerak bo'lgan
    kalit nomi HECH QAYERDA yozilmagan bo'lardi.
    """
    declared = {
        line.split("=", 1)[0]
        for line in SCANNED[ENV_EXAMPLE].splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    }
    missing = [key for key in ENV_KEYS if key not in declared]
    assert not missing, (
        f"`.env.example` da e'lon qilinmagan kalit(lar): {missing}. "
        "Ular `compose.yaml` ning `backup` blokida `${...}` bilan "
        "o'qiladi, ya'ni namunada bo'lmasa yangi o'rnatmada jimgina bo'sh "
        "qoladi."
    )
