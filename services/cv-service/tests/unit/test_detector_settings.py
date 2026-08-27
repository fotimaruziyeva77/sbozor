"""ARTEFAKT ISHGA TUSHISHDA TEKSHIRILADI — BIRINCHI KADRDA EMAS (§4.1, D-24).

=============================================================================
BU FAYL REJANING FAYL RO'YXATIDA YO'Q EDI — VA U ONGLI QO'SHIMCHA.

Reja `app/settings.py` ni Task 3 ning fayllari orasida sanaydi va
qabul mezoni sifatida shuni talab qiladi:

    «`CV_MODEL_PATH` mavjud bo'lmagan yo'lga qo'yilganda ilova ISHGA
     TUSHISHDA yiqiladi (`ValidationError`), birinchi chaqiruvda emas»

`field_validator` ning O'ZI 05-02 da yozilgan, lekin uni O'LCHAYDIGAN
test yo'q edi — ya'ni mezon KOD O'QIB tasdiqlanardi, xulq bilan emas.
Bu fayl o'sha bo'shliqni yopadi.

=============================================================================
NEGA «ISHGA TUSHISHDA» FARQ QILADI.

ONNX artefaktini `ops` qo'yadi (`ops/models/README.md`) va u UNUTILISHI
mumkin. Tekshiruv birinchi kadrga qoldirilsa:

    konteyner MUVAFFAQIYATLI ko'tariladi   ->  monitoring yashil
    nosozlik ertalab 06:00 da chiqadi      ->  hech kim qaramayotgan payt
    o'sha kunning kadrlari aniqlanmaydi    ->  kunlik hisob YO'QOLADI

`field_validator` esa uni deploy paytida, `docker compose logs
cv-service` da ochiq ko'rinadigan qilib to'xtatadi.
=============================================================================
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Final

import pytest
from pydantic import ValidationError

from app.settings import (
    DEFAULT_MODEL_PATH,
    MAX_INTRA_OP_THREADS,
    MIN_INTRA_OP_THREADS,
    Settings,
)

REQUIRED_SECRETS: Final[dict[str, Any]] = {
    "database_url": "postgresql+asyncpg://u:p@db:5432/sbozor",
    "s3_access_key": "test-access-key",
    "s3_secret_key": "test-secret-key",
}
"""`Settings` ning boshqa MAJBURIY maydonlari.

⚠ Ular shu yerda ATAYIN ochiq beriladi: muhitdan o'qilsa, test
  `compose.yaml` ning holatiga bog'liq bo'lib qolardi va boshqa
  mashinada boshqa natija berardi.
"""


def _settings(**overrides: Any) -> Settings:
    return Settings(**{**REQUIRED_SECRETS, **overrides})


def test_a_missing_model_file_is_rejected_at_construction() -> None:
    """Mavjud bo'lmagan `CV_MODEL_PATH` -> `ValidationError`, DARHOL.

    ⚠ Bu «fayl bormi?» degan test emas — «QACHON tekshiriladi?» degan
      test. Xato `Settings` QURILAYOTGANDA chiqadi, ya'ni
      `_open_worker_resources()` da, `WORKER_STARTUP` ilmog'ida.
    """
    with pytest.raises(ValidationError) as error:
        _settings(cv_model_path=Path("/nonexistent/rfdetr-large.onnx"))

    message = str(error.value)
    assert "CV_MODEL_PATH" in message
    assert "ops/models/README.md" in message, (
        "xato matni artefaktni QAYERDAN olishni aytmayapti — uni qo'ymagan "
        "odam javobni AYNAN shu satrdan olishi kerak"
    )


def test_a_directory_is_not_accepted_in_place_of_the_artefact(tmp_path: Path) -> None:
    """Katalog fayl o'rniga QABUL QILINMAYDI.

    `Dockerfile` `COPY ops/models/ /app/models/` qiladi, ya'ni katalog
    HAR DOIM mavjud bo'ladi — artefakt qo'yilmagan bo'lsa ham. Tekshiruv
    `exists()` ga tayansa, u aynan shu holatda YASHIL bo'lib, nosozlikni
    `onnxruntime` ga surib qo'yardi.
    """
    with pytest.raises(ValidationError):
        _settings(cv_model_path=tmp_path)


def test_an_existing_artefact_is_accepted(tmp_path: Path) -> None:
    """Fayl mavjud bo'lsa — qabul qilinadi (yuqoridagi ikkisining jufti).

    ⚠ Usiz `field_validator` HAR QANDAY yo'lni rad etsa ham testlar
      yashil bo'lardi va sozlama umuman ishlamas edi.
    """
    artefact = tmp_path / "rfdetr-large.onnx"
    artefact.write_bytes(b"not a real graph, but a real file")

    settings = _settings(cv_model_path=artefact)

    assert settings.cv_model_path == artefact


def test_the_default_path_matches_the_dockerfile_copy_target() -> None:
    """Standart yo'l `Dockerfile` ning `COPY` nishoni bilan JUFT.

    ⚠ Ikkalasi BIRGA o'zgaradi. Uchinchi nusxa (masalan `.env.example`
      dagi qattiq qiymat) jimgina ajralib ketardi.
    """
    dockerfile = Path(__file__).resolve().parents[2] / "Dockerfile"
    source = dockerfile.read_text(encoding="utf-8")

    assert "COPY ops/models/ /app/models/" in source
    assert str(DEFAULT_MODEL_PATH).replace("\\", "/").startswith("/app/models/")


@pytest.mark.parametrize("threads", [0, MAX_INTRA_OP_THREADS + 1])
def test_an_implausible_thread_count_is_rejected(threads: int, tmp_path: Path) -> None:
    """`intra_op_num_threads` chegaradan tashqarida bo'lolmaydi.

    `0` `onnxruntime` da «o'zing tanla» degani va u sozlamani JIMGINA
    ma'nosiz qilardi; `256` esa Contabo VPS'da kontekst almashinuviga
    ketardi. Chegara optimalni MAJBURLAMAYDI (D-08 — kechikish darvoza
    emas), faqat xato yozilgan qiymatni ushlaydi.

    ⚠⚠ `cv_model_path` MAVJUD FAYLGA qo'yiladi va bu ATAYIN. Standart
       yo'l (`/app/models/rfdetr-large.onnx`) test konteynerida YO'Q
       (`Dockerfile` ning `dev` bosqichi modelni ko'chirmaydi), ya'ni uni
       ishlatgan test `ValidationError` ni MODEL YO'LI uchun olib, chegara
       tekshiruvi umuman ishlamagan holda ham YASHIL bo'lardi. Xato
       maydonining nomi shu sababdan alohida tasdiqlanadi.
    """
    artefact = tmp_path / "rfdetr-large.onnx"
    artefact.write_bytes(b"placeholder")

    with pytest.raises(ValidationError) as error:
        _settings(cv_model_path=artefact, cv_intra_op_threads=threads)

    failed_fields = {str(item["loc"][0]) for item in error.value.errors()}
    assert failed_fields == {"cv_intra_op_threads"}, (
        f"yiqilgan maydonlar {failed_fields} — kutilgani faqat "
        "`cv_intra_op_threads`. Boshqa maydon ham yiqilsa, bu test chegarani "
        "emas, BOSHQA validatorni o'lchagan bo'lardi."
    )


def test_the_thread_bounds_are_a_sane_window() -> None:
    """Chegaralarning O'ZI mantiqiy — quyi chegara yuqoridan kichik."""
    assert MIN_INTRA_OP_THREADS >= 1
    assert MAX_INTRA_OP_THREADS > MIN_INTRA_OP_THREADS
