"""cv-service konfiguratsiyasi — 12-faktor uslubida, muhit o'zgaruvchilaridan.

`services/core-api/app/settings.py` naqshi: bitta `Settings` obyekti, har
entrypoint uni TO'LIQ quradi, sirlar faqat muhitdan keladi.

=============================================================================
⚠⚠ MODEL FAYLI ISHGA TUSHISHDA TEKSHIRILADI — BIRINCHI KADRDA EMAS.

Bu qaror 05-PATTERNS §4.1 da alohida yozilgan va sabab operatsion: ONNX
artefakti `ops` tomonidan qo'yiladi (D-24, `ops/models/README.md`) va u
UNUTILISHI mumkin. Tekshiruv birinchi kadrga qoldirilsa, konteyner
muvaffaqiyatli KO'TARILARDI va nosozlik ertalab 06:00 da — hech kim
qaramayotgan paytda — chiqardi. `field_validator` esa uni deploy paytida,
`docker compose logs cv-service` da ochiq ko'rinadigan qilib to'xtatadi.

Bu `core-api` dagi `NVR_CREDENTIAL_KEY`/`S3_ACCESS_KEY` validatorlarining
aynan bir xil sinfidagi qaror (T-03-22, T-04-29).
=============================================================================
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_MODEL_PATH = Path("/app/models/rfdetr-large.onnx")
"""Image ichidagi yo'l — `Dockerfile` ning `COPY ops/models/ /app/models/` i bilan JUFT.

⚠ IKKALASI BIRGA O'ZGARADI. Yo'l faqat shu yerda va Dockerfile'da uchraydi;
  uchinchi nusxa (masalan `.env.example` da qattiq qiymat) ajralib ketardi.
"""

MIN_INTRA_OP_THREADS = 1
MAX_INTRA_OP_THREADS = 16
"""`onnxruntime` ning `intra_op_num_threads` chegaralari.

Yuqori chegara Contabo VPS ning vCPU soniga (4–6) nisbatan KENG qo'yilgan:
u «xato yozilgan qiymat» ni (masalan `0` yoki `256`) ushlash uchun, optimal
qiymatni majburlash uchun EMAS.

⚠ OPTIMAL QIYMAT 05-07 DA O'LCHANMADI — VA BU ONGLI QAROR (D-08).
  RESEARCH §B.3 arifmetikasi savolni ahamiyatsiz qildi: 175 kadr/kun/bozor
  da eng og'ir ssenariy ham ~47 daqiqa CPU/kun, ya'ni kechikish bu
  fazaning chegarasi EMAS va §B.3 «reja EPYC'da benchmarkni DARVOZA qilib
  qo'ymasin» deb ochiq yozgan. Qiymat ≈ vCPU soni bo'lib qoladi va
  operatsion tarzda sozlanadi; o'lchov (`test_inference_budget.py`)
  foydali, lekin u fazani bloklamaydi.
"""


class Settings(BaseSettings):
    """cv-service ning YAGONA sozlama obyekti.

    ⚠ ENTRYPOINT BO'YICHA BO'LINMAYDI (`core-api` ning `compose.yaml`
      izohidagi o'lchangan qaror): ikki model jimgina ajralib ketardi va
      bir entrypoint qo'shgan maydonni ikkinchisi ko'rmay qolardi.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Aniqlagich (05-07) ---
    cv_model_path: Path = DEFAULT_MODEL_PATH
    cv_intra_op_threads: Annotated[int, Field(ge=MIN_INTRA_OP_THREADS, le=MAX_INTRA_OP_THREADS)] = 4

    # --- Baza va navbat ---
    database_url: str
    valkey_url: str = "redis://cache:6379/0"

    # --- Ombor: kadrni O'QISH va dalil rasmini yozish (05-08) ---
    s3_endpoint_url: str = "http://storage:8333"
    s3_bucket: str = "sbozor-snapshots"
    s3_access_key: str
    s3_secret_key: SecretStr

    # --- Kuzatuv ---
    sentry_dsn: str = ""
    log_level: str = "info"

    @field_validator("cv_model_path")
    @classmethod
    def _validate_model_file(cls, value: Path) -> Path:
        """ONNX artefakti ISHGA TUSHISHDA mavjud bo'lishi SHART (D-24, §4.1).

        Xato matni FAYL YO'LINI va YO'RIQNOMANI beradi: artefakt repoda
        saqlanmaydi (yuzlab MB, `git-lfs` yo'q), ya'ni uni qo'ymagan odam
        «nega yo'q?» degan savolga javobni shu satrdan olishi kerak.
        """
        if not value.is_file():
            raise ValueError(
                f"CV_MODEL_PATH ({value}) topilmadi. ONNX artefakti repoda "
                "SAQLANMAYDI — uni `ops` qo'yadi va image build paytida "
                "`COPY` qiladi. Eksport retsepti va fayl nomi: "
                "`ops/models/README.md`."
            )
        return value

    @field_validator("s3_access_key")
    @classmethod
    def _validate_s3_access_key(cls, value: str) -> str:
        """Bo'sh ombor kalitini ISHGA TUSHISHDA rad etadi (T-05-06).

        `core-api/app/settings.py` naqshi. Xato matnida KALIT NOMI bor,
        lekin QIYMAT yo'q — rad etilgan qiymat ta'rifi bo'yicha ishonchsiz.
        """
        if not value.strip():
            raise ValueError(
                "S3_ACCESS_KEY bo'sh bo'lishi mumkin emas. `cv-service` "
                "kadrlarni FAQAT O'QIYDI, lekin rekvizitsiz u umuman "
                "ko'tarilmasligi kerak (`ops/seaweedfs/README.md`)."
            )
        return value

    @field_validator("s3_secret_key")
    @classmethod
    def _validate_s3_secret_key(cls, value: SecretStr) -> SecretStr:
        """Bo'sh ombor maxfiy kalitini ISHGA TUSHISHDA rad etadi (T-05-06)."""
        if not value.get_secret_value().strip():
            raise ValueError(
                "S3_SECRET_KEY bo'sh bo'lishi mumkin emas. U "
                "`ops/seaweedfs/s3.json` dagi qiymat bilan AYNAN bir xil "
                "bo'lishi shart (`ops/seaweedfs/README.md`)."
            )
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Sozlamalarni bir marta o'qiydi va keshlaydi (`core-api` naqshi)."""
    # mypy majburiy maydonlarni argument sifatida kutadi, lekin
    # pydantic-settings ularni MUHITDAN to'ldiradi.
    return Settings()  # type: ignore[call-arg]
