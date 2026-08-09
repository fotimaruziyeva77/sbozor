"""ONNX sessiya — loyihaning BIRINCHI inference kodi (§4.1, RESEARCH §B.2/§B.3).

=============================================================================
ANALOG YO'Q — VA BU O'LCHANGAN FAKT.

05-PATTERNS §4.1 repoda `onnx|rfdetr|supervision|torch|numpy|opencv` bo'yicha
ijro etiladigan koddan **NOL** natija topdi. Ya'ni bu yerdagi hech narsa
mavjud naqshdan ko'chirilmagan; eng yaqin strukturaviy qo'shni —
`core-api/app/worker.py:181-207` dagi «og'ir resursning umri» shakli.

⚠ LEKIN FARQ MUHIM: ONNX sessiyasi — **JARAYON-LOKAL** resurs, tarmoq
  resursi EMAS. Uni «qayta ulanish» tushunchasi yo'q; u yo ochiladi, yo
  jarayon umuman ishga tushmaydi.

=============================================================================
⚠⚠ REZOLYUTSIYA GRAFDAN O'QILADI, QATTIQ YOZILMAYDI.

`session.get_inputs()[0].shape[2:4]` — model varianti almashganda
(`RFDETRLarge` -> boshqasi) kod O'ZGARMASLIGI uchun. Qattiq yozilgan
raqam eng yomon shakldagi nosozlikni berardi: kirish tenzori noto'g'ri
o'lchamda bo'lsa `onnxruntime` ISTISNO TASHLAMAYDI — u shunchaki
boshqacha natija qaytaradi, ya'ni aniqlik jimgina tushardi.

=============================================================================
⚠⚠ `providers` ATAYIN YOZILADI.

`providers=["CPUExecutionProvider"]` — standartga TAYANILMAYDI.
`onnxruntime` provayderlar ro'yxatini o'zi tanlaganda, image'ga bir kun
GPU provayderi kirib qolsa, u jimgina tanlanardi va Contabo VPS'da
(GPU'siz) nosozlik ish paytida ochilardi.

=============================================================================
KECHIKISH BU FAZANING CHEGARASI EMAS (D-08, RESEARCH §B.3).

175 kadr/kun/bozor da eng og'ir ssenariy ham ~47 daqiqa CPU/kun. Ya'ni
variant (`RFDETRLarge`) **aniqlik** uchun tanlangan va bu modul tezlik
uchun optimallashtirilmaydi. `intra_op_num_threads` ≈ vCPU soni —
sozlama, darvoza EMAS.
=============================================================================
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import cv2
import numpy as np
import numpy.typing as npt
import onnxruntime as ort

__all__ = [
    "EXPECTED_OUTPUT_COUNT",
    "IMAGENET_MEAN",
    "IMAGENET_STD",
    "INPUT_TENSOR_NAME",
    "DetectorSession",
]

INPUT_TENSOR_NAME: Final = "input"
"""Grafning kirish nomi — rasmiy eksport misolidan (RESEARCH §B.2).

⚠ Bu nom TEKSHIRILADI, taxmin qilinmaydi: konstruktor haqiqiy grafdagi
  nomni o'qiydi va mos kelmasa ISHGA TUSHISHDA yiqiladi. Noto'g'ri nom
  bilan `session.run()` `InvalidArgument` berardi — lekin faqat BIRINCHI
  KADRDA, ya'ni ertalab 06:00 da.
"""

IMAGENET_MEAN: Final[tuple[float, float, float]] = (0.485, 0.456, 0.406)
IMAGENET_STD: Final[tuple[float, float, float]] = (0.229, 0.224, 0.225)
"""ImageNet normalizatsiyasi — rasmiy eksport misolidan (RESEARCH §B.2).

⚠ TARTIB **RGB**, BGR EMAS. `cv2.imdecode` esa **BGR** qaytaradi —
  quyidagi `preprocess()` ni o'qing.
"""

EXPECTED_OUTPUT_COUNT: Final = 2
"""Graf AYNAN ikkita tenzor qaytaradi: `dets` va `labels`.

⚠ Bu shart ISHGA TUSHISHDA tekshiriladi va sabab jim nosozlikda: boshqa
  shakldagi eksport (masalan segmentatsiya varianti) uchinchi tenzor
  qo'shardi va pozitsion o'qish `labels` o'rniga BOSHQA tenzorni olardi.
  Istisno chiqmasdi — post-processing shunchaki bema'ni ballar bilan
  ishlardi.
"""

_SPATIAL_DIMS: Final = slice(2, 4)
"""NCHW tartibidagi `(balandlik, kenglik)` o'qlari."""

_CHANNELS: Final = 3


class DetectorSession:
    """`onnxruntime` sessiyasining EGASI — jarayonda BITTA nusxa.

    Umri `core-api/app/worker.py` ning `WORKER_STARTUP`/`WORKER_SHUTDOWN`
    juftligi bilan bir xil shaklda boshqariladi va u 05-08 da ulanadi.
    Har kadrda yangi sessiya qurish grafni qaytadan yuklab, optimizatsiya
    o'tkazardi — bu kadr boshiga soniyalar demakdir.

    ⚠ BU KLASS SOXTALASHTIRILMAYDI. `tests/unit/test_detector_has_no_stub.py`
      `app/**` daraxtida `InferenceSession` chaqiruvi AYNAN BITTA joyda
      ekanini AST bilan tekshiradi. Sabab 03-14 va 04-12 da ikki marta
      o'lchangan: birinchi «qulaylik uchun» soxta amalga oshirilish butun
      inference yo'lini O'LCHANMAGAN qoldiradi.
    """

    def __init__(self, model_path: Path, *, intra_op_num_threads: int) -> None:
        """Sessiyani ochadi va grafning kontraktini TEKSHIRADI.

        Args:
            model_path: `.onnx` artefaktining yo'li. Mavjudligi allaqachon
                `Settings` ning `field_validator` ida tekshirilgan — bu
                yerda u YANA tekshirilmaydi, chunki ikki joyda turgan bir
                xil xato matni ajralib ketardi.
            intra_op_num_threads: ≈ vCPU soni (D-08 — sozlama, darvoza emas).

        Raises:
            ValueError: graf kutilgan kontraktga mos kelmasa (kirish nomi,
                chiqishlar soni yoki statik bo'lmagan rezolyutsiya).
        """
        options = ort.SessionOptions()
        options.intra_op_num_threads = intra_op_num_threads

        # ⚠ `providers` ATAYIN — modul docstringidagi sabab.
        self._session = ort.InferenceSession(
            str(model_path), options, providers=["CPUExecutionProvider"]
        )

        graph_input = self._session.get_inputs()[0]
        self._input_name: str = graph_input.name

        if self._input_name != INPUT_TENSOR_NAME:
            raise ValueError(
                f"grafning kirish nomi `{self._input_name}`, kutilgani "
                f"`{INPUT_TENSOR_NAME}` (RESEARCH §B.2). Nom mos kelmasa "
                "`session.run()` faqat BIRINCHI KADRDA yiqilardi."
            )

        outputs = self._session.get_outputs()
        if len(outputs) != EXPECTED_OUTPUT_COUNT:
            raise ValueError(
                f"graf {len(outputs)} ta tenzor qaytaradi, kutilgani "
                f"{EXPECTED_OUTPUT_COUNT} (`dets` va `labels`). Boshqa "
                "shakldagi eksport pozitsion o'qishni JIMGINA buzardi."
            )

        # ⚠⚠ REZOLYUTSIYA GRAFDAN — `session.get_inputs()[0].shape[2:4]`.
        height, width = self._session.get_inputs()[0].shape[_SPATIAL_DIMS]
        if not isinstance(height, int) or not isinstance(width, int):
            raise ValueError(
                f"grafning kirish rezolyutsiyasi statik emas: {(height, width)}. "
                "Eksport qat'iy `shape` bilan qilinadi (`ops/models/README.md`); "
                "dinamik o'q bo'lsa kadr o'lchami har chaqiruvda TAXMIN "
                "qilinardi."
            )
        self._input_size: tuple[int, int] = (width, height)

    @property
    def input_size(self) -> tuple[int, int]:
        """`(kenglik, balandlik)` — GRAFDAN o'qilgan, qattiq yozilmagan."""
        return self._input_size

    @property
    def input_name(self) -> str:
        """Grafning kirish tenzori nomi."""
        return self._input_name

    def preprocess(self, frame_bytes: bytes) -> npt.NDArray[np.float32]:
        """Kadr baytlarini grafning kirish tenzoriga aylantiradi.

        Bosqichlar (rasmiy misoldan, RESEARCH §B.2):
            dekod -> BGR->RGB -> `resize(w, h)` -> `/255.0`
            -> ImageNet `mean`/`std` -> `transpose(2,0,1)` -> `expand_dims(0)`

        ⚠⚠ `BGR -> RGB` NI TUSHIRIB QOLDIRISH JIM NOSOZLIK.
           `cv2.imdecode` **BGR** qaytaradi, ImageNet statistikasi esa
           **RGB** uchun. Kanallar almashtirilmasa hech qanday istisno
           chiqmaydi — model shunchaki YOMONROQ ishlaydi va nosozlik
           «aniqlik past» bo'lib ko'rinadi, ya'ni model sifatiga
           yozilardi.

        ⚠ `cv2.imdecode` buzuq baytda `None` QAYTARADI, istisno tashlamaydi
          (o'lchandi). Bu `None` keyingi qatorda `AttributeError` berardi
          va sabab «buzuq kadr» emas, «kod xatosi» bo'lib ko'rinardi
          (T-05-30).

        Raises:
            ValueError: baytlar tasvir sifatida dekodlanmasa.
        """
        buffer = np.frombuffer(frame_bytes, dtype=np.uint8)
        decoded = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        if decoded is None:
            raise ValueError(
                f"kadr dekodlanmadi ({len(frame_bytes)} bayt). `cv2.imdecode` "
                "buzuq baytda `None` qaytaradi — bu holat SHU YERDA "
                "to'xtatiladi (T-05-30)."
            )

        width, height = self._input_size
        # ⚠ Kanal tartibi AVVAL, o'lcham keyin — ikkalasi mustaqil.
        rgb = cv2.cvtColor(decoded, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (width, height), interpolation=cv2.INTER_LINEAR)

        scaled = resized.astype(np.float32) / 255.0
        mean = np.array(IMAGENET_MEAN, dtype=np.float32)
        std = np.array(IMAGENET_STD, dtype=np.float32)
        normalised: npt.NDArray[np.float32] = ((scaled - mean) / std).astype(np.float32)

        tensor: npt.NDArray[np.float32] = np.expand_dims(
            normalised.transpose(2, 0, 1), axis=0
        ).astype(np.float32)
        return tensor

    def run(
        self, tensor: npt.NDArray[np.float32]
    ) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
        """Grafni yuritadi va XOM tenzorlarni qaytaradi.

        ⚠ POST-PROCESSING BU YERDA EMAS. Sigmoid, background ustuni va
          koordinata konversiyasi `postprocess.raw_to_detections()` da —
          ular SOF ARIFMETIKA va shu sababdan real artefaktsiz to'liq
          testlanadi (D-02 ning chokи).

        Returns:
            `(dets, labels)` — POZITSION tartibda, eksport qanday bergan
            bo'lsa shunday. ⚠ Tartibning O'ZI `[LOW confidence]`: rasmiy
            hujjat ikkala tenzorni nomlaydi, lekin tartibni ochiq
            aytmaydi. Uni haqiqiy artefakt ustida `model` markerli test
            o'lchaydi (`tests/integration/test_onnx_session.py`).
        """
        dets, labels = self._session.run(None, {self._input_name: tensor})
        return dets, labels
