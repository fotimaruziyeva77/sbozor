"""Ombor konfiguratsiyasining darvozasi (04-01, W0-3/W0-4, T-04-01/02/04).

=============================================================================
BU FAYL IKKI MUSTAQIL «JIMGINA YOLG'ON» NI YOPADI.

**1. `anonymous` identity (T-04-01).** SeaweedFS ning rasmiy
`docker/compose/s3.json` misoli AYNAN shunday boshlanadi:

    { "identities": [ { "name": "anonymous", "actions": ["Read"] }, ... ] }

Misolni nusxalash BARCHA bozorlarning dalil-kadrlarini portga yeta
oladigan har kimga beradi. Kadrlar — bozor tashrifchilarining shaxsiy
ma'lumoti va O'zR qonuni ostidagi ma'lumot. Nosozlik SIGNALSIZ: ombor
bemalol ishlaydi, hech qanday xato chiqmaydi, farq faqat kimdir uni
topganda ko'rinadi.

**2. `scheduler` ning profil ortida qolishi (T-04-04).** Planer profilga
tushib qolsa kunlik reja HECH QACHON materializatsiya bo'lmasdi va HECH
QANDAY XATO CHIQMASDI — `docker compose ps` toza, jurnal bo'sh, jadval
jimgina bo'sh. Nosozlik faqat kun oxirida, hisobot bo'sh chiqqanda
sezilardi.

=============================================================================
NEGA `json.loads`, NEGA `grep` EMAS:

`grep -q anonymous` uchta xato beradi: (a) `anonymous` so'zi IZOHDA
uchrasa yolg'on-qizil; (b) `"name": "anonymous_reader"` ni tutmaydi degan
taassurot beradi, aslida tutadi va bu ham chalkashlik; (c) eng muhimi —
u `actions` ning BUCKETGA QADALGANLIGINI umuman o'lchay olmaydi. Parser
esa strukturani ko'radi: kalit nomini uning qiymatidan, qiymatni esa
matn ichidagi tasodifiy uchrashuvdan ajratadi.

NEGA `compose.yaml` QO'LDA PARSE QILINADI:
`PyYAML` bu loyihaning bog'liqligi EMAS va uni FAQAT shu test uchun
qo'shish `dev` guruhiga yangi paket kiritardi. `test_compose_sim_env.py`
allaqachon `compose.yaml` ni matn sifatida o'qish naqshini o'rnatgan;
bu yerda undan bir pog'ona yuqoriga chiqiladi (servis bloklariga
ajratish), lekin qaram bo'lish darajasi o'zgarmaydi. Parserning O'ZI
quyi chegara bilan qo'riqlanadi (pastdagi birinchi test).
=============================================================================
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
S3_CONFIG_EXAMPLE = REPO_ROOT / "ops" / "seaweedfs" / "s3.json.example"
COMPOSE = REPO_ROOT / "compose.yaml"

BUCKET = "sbozor-snapshots"
"""Yagona bucket. Bozor boshiga bucket EMAS — yangi bozor onboardingiga
«bucket yarat + IAM yozuvi qo'sh» qadamini qo'shish self-service
qoidasini buzardi. Tenant izolyatsiyasi ilova + DB da, prefiks bilan."""

PROFILELESS_SERVICES = ("storage", "scheduler")
"""Ishlab chiqarish komponentlari — `npm run up` ularni ham ko'taradi.

`worker` va `go2rtc` bilan aynan bir xil qaror (`compose.yaml:168-172`).
`scheduler` uchun oqibat eng qimmat: profil ortida qolgan planer
hech qanday xato bermasdan butun kunlik rejani yo'qotardi (W0-3).
"""

MIN_COMPOSE_SERVICES = 8
"""Quyi chegara — parser buzilganda darvoza JIMGINA yashil bo'lardi.

2026-08-04 holati: `db`, `cache`, `storage`, `migrate`, `core-api`,
`worker`, `scheduler`, `go2rtc`, `frontend`, `nginx`, `nvr-sim`,
`nvr-sim-rtsp`, `tests` — o'n uchta. Chegara pastki, ya'ni servis
qo'shilganda qayta ko'rib chiqilmaydi.
"""


def _strip_full_line_comments(text: str) -> list[str]:
    """FAQAT butun-qator izohlar tashlanadi (`test_compose_sim_env.py` qoidasi).

    Qator oxiridagi izoh QOLDIRILADI: uni kesish uchun `#` ni satr ichida
    izlash kerak bo'lardi va u YAML qiymatidagi `#` ni ham kesib yuborardi.
    """
    return [line for line in text.splitlines() if not line.lstrip().startswith("#")]


def _compose_services() -> dict[str, list[str]]:
    """`compose.yaml` -> `{servis nomi: [uning birinchi darajali kalitlari]}`.

    Faqat SHAKL o'qiladi (qaysi kalit bor/yo'q), qiymatlar emas — bu
    testlar aynan kalitning MAVJUDLIGI haqida da'vo qiladi (`ports:`
    bo'lmasligi, `profiles:` bo'lmasligi, `healthcheck:` bo'lmasligi).
    """
    lines = _strip_full_line_comments(COMPOSE.read_text(encoding="utf-8"))

    services: dict[str, list[str]] = {}
    current: str | None = None
    in_services = False

    for line in lines:
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))

        if indent == 0:
            in_services = line.startswith("services:")
            current = None
            continue
        if not in_services:
            continue

        stripped = line.strip()
        if indent == 2 and stripped.endswith(":"):
            current = stripped[:-1]
            services[current] = []
        elif indent == 4 and current is not None and ":" in stripped:
            services[current].append(stripped.split(":", 1)[0].strip())

    return services


@pytest.fixture(scope="module")
def s3_config() -> dict[str, Any]:
    assert S3_CONFIG_EXAMPLE.is_file(), (
        f"{S3_CONFIG_EXAMPLE} topilmadi — `ops/seaweedfs/README.md` bu faylni "
        "`cp s3.json.example s3.json` naqshining manbai deb ko'rsatadi"
    )
    data: dict[str, Any] = json.loads(S3_CONFIG_EXAMPLE.read_text(encoding="utf-8"))
    return data


@pytest.fixture(scope="module")
def compose_services() -> dict[str, list[str]]:
    return _compose_services()


# --------------------------------------------------------------------------
# T-04-01: `s3.json` — `anonymous` tuzog'i va huquqlarning kengligi
# --------------------------------------------------------------------------


def test_exactly_one_identity(s3_config: dict[str, Any]) -> None:
    """AYNAN bitta rekvizit — har qo'shimchasi yana bitta oqish yuzasi.

    Ilovada bitta S3 mijozi bor (`core-api` kod bazasi: `core-api`,
    `worker`, `scheduler`). Ikkinchi identity qo'shilishi «kimdir yana
    kimgadir kirish bergan» degani va u shu yerda ko'rinadi.
    """
    identities = s3_config["identities"]
    assert len(identities) == 1, (
        f"`s3.json.example` da {len(identities)} ta identity bor "
        f"({[i.get('name') for i in identities]}), kutilgani — AYNAN BITTA. "
        "Har qo'shimcha rekvizit yana bitta oqish yuzasi."
    )
    assert identities[0]["name"] == "sbozor-core-api", (
        f"identity nomi `{identities[0]['name']}` — kutilgani `sbozor-core-api`. "
        "Nom `.env` va `README.md` bilan mos bo'lishi kerak."
    )


def test_no_anonymous_identity(s3_config: dict[str, Any]) -> None:
    """⚠⚠ `anonymous` YO'Q — rasmiy misol fayldagi TUZOQ (T-04-01).

    SeaweedFS ning `docker/compose/s3.json` misoli
    `{"name": "anonymous", "actions": ["Read"]}` bilan boshlanadi va uni
    nusxalash butun dalil arxivini AUTENTIFIKATSIYASIZ o'qishga ochadi.
    Nosozlik hech qanday signal bermaydi — ombor bemalol ishlaydi.
    """
    names = [str(identity.get("name", "")).strip().lower() for identity in s3_config["identities"]]

    assert "anonymous" not in names, (
        "`s3.json.example` da `anonymous` identity bor — bu BUTUN dalil "
        "arxivini autentifikatsiyasiz o'qishga ochadi (T-04-01). Yozuv "
        "SeaweedFS ning rasmiy misolidan ko'chib kelgan bo'lishi mumkin; "
        "uni O'CHIRING. Sabab: `ops/seaweedfs/README.md` §1."
    )


def test_every_action_is_scoped_to_the_bucket(s3_config: dict[str, Any]) -> None:
    """Har bir amal `Action:bucket` shaklida — bucketsiz `Read` KLASTERGA tegishli.

    `"Read"` (ikki nuqtasiz) SeaweedFS'da butun klasterga ruxsat beradi,
    ya'ni kelajakdagi har qanday bucket ham ochilib ketardi. Chegara
    yozuvda bo'lishi shart, intizomda emas.
    """
    problems: list[str] = []
    for identity in s3_config["identities"]:
        for action in identity.get("actions", []):
            if ":" not in action:
                problems.append(f"{identity['name']}: `{action}` bucketga QADALMAGAN")
                continue
            verb, _, scope = action.partition(":")
            if scope.split("/", 1)[0] != BUCKET:
                problems.append(f"{identity['name']}: `{action}` -> `{BUCKET}` emas ({verb})")

    assert not problems, (
        "S3 huquqlari bucket chegarasidan chiqadi:\n  "
        + "\n  ".join(problems)
        + f"\nHar bir amal `<Amal>:{BUCKET}` shaklida bo'lishi shart."
    )


def test_no_admin_action(s3_config: dict[str, Any]) -> None:
    """`Admin` berilmaydi — ilova bucket yaratmaydi/o'chirmaydi.

    Bucket bir marta, QO'LDA yaratiladi (`README.md` §3) va aynan shu
    sababdan `app/services/storage.py` da `create_bucket` chaqiruvi
    BO'LMAYDI (04-06). `Admin` qo'shilishi o'sha qarorning teskariga
    aylanganini bildiradi va u code review'da ko'rinishi kerak.
    """
    admin_actions = [
        action
        for identity in s3_config["identities"]
        for action in identity.get("actions", [])
        if action.partition(":")[0].strip().lower() == "admin"
    ]

    assert not admin_actions, (
        f"`Admin` amali berilgan: {admin_actions}. Ilovaga bucket yaratish/"
        "o'chirish kerak emas — bucket bir marta qo'lda yaratiladi "
        "(`ops/seaweedfs/README.md` §3)."
    )


# --------------------------------------------------------------------------
# T-04-02 / T-04-04: `compose.yaml` — port publish va profillar
# --------------------------------------------------------------------------


def test_compose_parser_actually_sees_the_services(compose_services: dict[str, list[str]]) -> None:
    """QUYI CHEGARA: bo'sh to'plamda quyidagi «yo'q» testlari JIMGINA o'tardi.

    Parser buzilsa (`compose.yaml` ko'chirilsa, otstuplar o'zgarsa) har
    bir «kalit yo'q» da'vosi ROST bo'lib qolardi — chunki servisning o'zi
    topilmagan bo'lardi. `test_compose_sim_env.py` dagi 1-qoida.
    """
    assert COMPOSE.is_file(), f"`{COMPOSE}` topilmadi — yo'l eskirgan"
    assert len(compose_services) >= MIN_COMPOSE_SERVICES, (
        f"`compose.yaml` dan faqat {len(compose_services)} servis topildi "
        f"({sorted(compose_services)}), kamida {MIN_COMPOSE_SERVICES} kutilgan. "
        "Parser bo'sh to'plamda ishlayotgan bo'lsa quyidagi assert'lar hech "
        "nimani isbotlamaydi."
    )
    # Nazorat qiymatlari: parser haqiqatan kalitlarni ko'rayotganini isbotlaydi.
    assert "ports" in compose_services["nginx"], (
        "`nginx` da `ports:` topilmadi — parser kalitlarni ko'rmayapti, ya'ni "
        "`storage` da ham hech nima topmasdi va test yolg'on-yashil bo'lardi"
    )
    assert "profiles" in compose_services["nvr-sim"], (
        "`nvr-sim` da `profiles:` topilmadi — parser profil kalitini ko'rmayapti, "
        "ya'ni profilsizlik da'vosi ham hech nimani isbotlamasdi"
    )


def test_storage_port_is_not_published(compose_services: dict[str, list[str]]) -> None:
    """`storage` da `ports:` YO'Q — `go2rtc` bilan aynan bir xil qoida (T-04-02).

    compose `ports:` bandi Docker'ning `iptables` qoidalarini yozadi va u
    host firewall'ini CHETLAB O'TADI — «UFW da yopiq» degan ishonch
    yolg'on bo'lib qolardi. Ombor barcha bozorlarning dalil-kadrlarini
    saqlaydi; rasmga yagona yo'l — `core-api` proxy endpointi (04-09).
    """
    assert "ports" not in compose_services["storage"], (
        "`storage` servisida `ports:` bloki paydo bo'lgan — 8333 xostga "
        "publish qilinsa butun dalil arxivi tarmoqqa ochiladi (T-04-02). "
        "Dev uchun kerak bo'lsa `compose.override.yml` da 127.0.0.1 ga "
        "bog'lang, bu yerda EMAS."
    )
    # Nazorat: `go2rtc` bilan bir xil sinfda ekani qulflanadi.
    assert "ports" not in compose_services["go2rtc"], (
        "`go2rtc` ga `ports:` qaytdi — GHSA-wwww-5h25-jf98 (CVSS 9.1) yuzasi"
    )


@pytest.mark.parametrize("service", PROFILELESS_SERVICES)
def test_production_service_has_no_profile(
    service: str, compose_services: dict[str, list[str]]
) -> None:
    """`storage` va `scheduler` PROFILSIZ — W0-3/W0-4 ning butun mazmuni.

    Profil ortidagi planer kunlik rejani HECH QANDAY XATO BERMASDAN
    yo'qotardi: `docker compose ps` toza, jurnal bo'sh, `capture_runs`
    jimgina bo'sh. Profil ortidagi ombor esa kadr yuklashni yiqitardi va
    sabab «tarmoq nosozligi» bo'lib ko'rinardi.

    ⚠ Bu darvoza `docker compose up scheduler` NI TALAB QILMAYDI va bu
      ataylab: `app.worker:scheduler` obyekti 04-07 da tug'iladi, W0-3
      esa profilsizlikni koddan OLDIN qulflashni talab qiladi. Ya'ni
      darvoza bugundan ishlaydi va 04-07 gacha yashil qoladi.
    """
    assert service in compose_services, (
        f"`{service}` servisi `compose.yaml` da umuman yo'q — W0-3/W0-4 bajarilmagan"
    )
    assert "profiles" not in compose_services[service], (
        f"`{service}` profil ortiga yashirilgan. U ISHLAB CHIQARISH komponenti: "
        "`npm run up` (profilsiz) uni ham ko'tarishi shart. `worker` va `go2rtc` "
        "bilan aynan bir xil qaror (`compose.yaml` dagi izohlar)."
    )


def test_scheduler_has_no_fake_healthcheck(compose_services: dict[str, list[str]]) -> None:
    """`scheduler` da `healthcheck:` YO'Q — soxta signal yolg'on ishonch berardi.

    `taskiq scheduler` HTTP yuzasi bermaydi va JARAYON TIRIKLIGI «tik
    ketyaptimi?» savoliga javob BERMAYDI. Aynan shu nosozlik sinfi
    3-fazada o'lchangan: konteyner `Up`, `docker compose ps` sog'lom
    ko'rsatadi va birorta vazifa hech qachon bajarilmaydi.

    Yagona ishonchli signal — BAZADAGI natija (`alert_sweep` va
    `/internal/self-check`, 04-07/04-08). RESEARCH Pitfall 14:
    heartbeat'ni konteyner `healthcheck` iga ULAMANG.
    """
    assert "healthcheck" not in compose_services["scheduler"], (
        "`scheduler` ga `healthcheck:` qo'shilgan. Jarayon tirikligi tik "
        "ketayotganini ISBOTLAMAYDI — bunday tekshiruv «sog'lom, lekin hech "
        "nima bajarilmayapti» holatini YASHIRADI. Tiriklik bazadan o'lchanadi "
        "(04-07 `/internal/self-check`), konteyner statusidan emas."
    )
    # Nazorat holati: `storage` da healthcheck BOR — ya'ni yuqoridagi
    # da'vo «hech kimda healthcheck yo'q» degan bo'sh gap emas.
    assert "healthcheck" in compose_services["storage"], (
        "`storage` da `healthcheck:` yo'qolgan — `nc -z 127.0.0.1 8333` "
        "`docker compose up --wait` ning yagona to'xtash signali"
    )
