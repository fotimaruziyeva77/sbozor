"""NVR domeni — tenant-scoped repozitoriy va SC#2 ning idempotent upserti.

=============================================================================
SIR CHEGARASI: BU MODUL PAROLNI KO'RMAYDI.

`put_credential()` va `get_credential()` FAQAT `bytes` bilan ishlaydi.
Shifrlash va deshifrlash `app/security/secrets.py` da, ya'ni SERVIS
qatlamida bajariladi — `user_repo.py` parolni ALLAQACHON hash bo'lgan
holda qabul qilgani bilan AYNAN bir xil chegara.

Nega chegara aynan shu yerda: repozitoriy shifrlasa har bir chaqiruvchi
"shifrlangan holda uzatsammikin yoki ochiq matnda?" degan savolga duch
kelardi va ikkala javob ham bir joyda ishlatilardi. Bir tomonlama qoida
("bu yerga faqat `bytes` kiradi") tekshirib bo'ladigan va buzib
bo'lmaydigan qoida.

⚠ `nvr_credentials` AUDIT TRIGGERIDAN CHIQARILGAN (03-03, T-03-13) —
  ya'ni shifrmatn `audit_log` ga tushmaydi. Bu jadvalga trigger ulash
  taklifi kelsa: kalit buzilganda audit TARIXIY parollarni ham berardi.
=============================================================================

TENANT FILTRI IKKI QATLAM: RLS policy'si himoya to'ri, `scoped()` esa
aniq `market_id` predikati (`tenancy.py:117-166`).

=============================================================================
NEGA XOM `text()` EMAS, SQLAlchemy Core — VA BU NEGA MUHIM.

`audit_repo.py:238-256` xom `text()` ishlatganda bind parametrlarini
QO'LDA tiplaydi (`bindparam(..., type_=...)`), chunki `text()` da
SQLAlchemy tipni ustundan chiqara olmaydi va tipsiz qiymat asyncpg'ga
xom `str`/`dict` bo'lib borardi. Bu modulda AYNAN SHU xavf bor:
`source_ip` — `inet`, `error_detail` — `jsonb`.

Shuning uchun bu yerda ikkinchi yo'l tanlandi: Core ifodalari
(`insert(Camera)`, `update(Camera)`). Ular tipni MODEL USTUNIDAN oladi,
ya'ni tiplash UNUTIB BO'LMAYDIGAN joyga — model ta'rifiga — bog'lanadi.
Xom SQL da tiplashni unutish JIMGINA ishlaydi (bir necha qiymat uchun)
va faqat chegara holatida yiqiladi; Core da esa unutadigan qadam yo'q.

⚠ Bu modulga xom `text()` qo'shilsa `audit_repo.py` naqshi MAJBURIY
  bo'ladi: `bindparam(..., type_=INET())` / `type_=JSONB()`.

Yagona joy — `upsert_cameras` dagi `literal_column("(xmax = 0)")`: bu
Postgres ning tizim ustuni va uning ORM ekvivalenti yo'q. U ATAYIN
tiplangan (`Boolean`), aks holda natija `Any` bo'lib qolardi.
=============================================================================

=============================================================================
QATTIQ O'CHIRISH BU MODULDA YO'Q VA BO'LMAYDI (D-10, Pitfall 11).

Yo'qolgan kanal `status = 'offline'` bo'ladi, qator esa QOLADI. Sabab
kelajakdagi bog'lanishlarda: 4-fazadagi snapshotlar va 5-fazadagi zona
poligonlari `cameras.id` ga tayanadi. Qatorni yo'q qilish tarixiy
DALILNI yo'q qilardi — «bu rasta o'sha kuni band edi» degan da'voning
rasm-asosi yetim qolardi.

Vaqtincha o'chgan kamera (elektr uzilishi, kabel) keyingi skanda o'z
qatoriga QAYTADI: kalit `(market_id, nvr_id, channel_no)` barqaror.
Agar qator o'chirilgan bo'lsa u yangi `id` bilan tug'ilardi va unga
bog'langan hamma narsa uzilardi.
=============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sbozor_core.enums import CameraStatus, DiscoveryRunStatus
from sbozor_core.models import Camera, NvrCredential, NvrDevice, NvrDiscoveryRun
from sbozor_core.tenancy import TenantScopedRepository
from sqlalchemy import Boolean, case, literal_column, select, update
from sqlalchemy.dialects.postgresql import Insert, insert

from app.repositories.audit_repo import mask_sensitive
from app.services.rtsp import new_stream_name

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy import Case

__all__ = [
    "ACTIVE_RUN_STATUSES",
    "DiscoveredChannel",
    "NvrRepository",
    "UpsertCounts",
]

ACTIVE_RUN_STATUSES: tuple[str, ...] = (
    DiscoveryRunStatus.QUEUED.value,
    DiscoveryRunStatus.RUNNING.value,
)
"""«Faol yugurish» to'plami — `0012` dagi qisman UNIQUE indeks bilan BIR XIL.

⚠ Ikki nusxa ATAYIN emas: qiymat `sbozor_core.models.nvr.
  DISCOVERY_RUN_ACTIVE_STATUSES` bilan bir xil enum a'zolaridan quriladi,
  ya'ni ro'yxat kengaysa ikkala tomon ham birga o'zgaradi.
"""


@dataclass(frozen=True)
class DiscoveredChannel:
    """Kashfiyot topgan BITTA kanal — ISAPI klientining (03-05) chiqishi.

    Repozitoriy uchun bu shunchaki qiymatlar to'plami: u ISAPI ni ham,
    XML ni ham bilmaydi. Shu sababdan klient DTO'si bu yerga import
    QILINMAYDI — bog'liqlik yo'nalishi repozitoriydan klientga emas,
    klientdan repozitoriyga.
    """

    channel_no: int
    name: str
    status: str = CameraStatus.ONLINE.value
    source_ip: str | None = None
    source_model: str | None = None
    has_substream: bool = True


@dataclass(frozen=True)
class UpsertCounts:
    """Bitta skanning natijasi — `nvr_discovery_runs` ustunlari bilan BIR XIL NOM.

    Nomlar ataylab jadval ustunlarini takrorlaydi: `finish_run()` ularni
    qayta nomlamasdan yozadi va oraliqda «qaysi son qaysi ustunga
    tushadi?» degan savol umuman tug'ilmaydi.

    `channels_marked_offline` boshida `0`: uni `mark_missing_offline()`
    beradi va u ATAYIN alohida qadam (upsert ko'rmagan kanallarni
    bilmaydi — u faqat ko'rganlarini biladi). Birlashtirish uchun
    `with_marked_offline()`.
    """

    channels_found: int
    channels_added: int
    channels_marked_offline: int = 0

    def with_marked_offline(self, count: int) -> UpsertCounts:
        """`mark_missing_offline()` natijasini qo'shib yangi nusxa qaytaradi."""
        return replace(self, channels_marked_offline=count)


class NvrRepository(TenantScopedRepository):
    """NVR qurilmalari, rekvizitlari, kameralari va kashfiyot yugurishlari.

    To'rtala jadval BITTA repozitoriyda va bu ataylab: ular bitta
    kashfiyot oqimida birga o'zgaradi (`create_run` -> `upsert_cameras`
    -> `mark_missing_offline` -> `finish_run`) va ularni to'rt modulga
    bo'lish o'sha oqimni to'rt import bilan yig'ishga majbur qilardi
    (`stall_repo.py` dagi «uchta repozitoriy, bitta modul» bilan bir xil
    qaror va bir xil sabab).
    """

    # ------------------------------------------------------------------
    # Qurilmalar
    # ------------------------------------------------------------------

    async def create_device(
        self,
        *,
        host: str,
        port: int,
        username: str,
        use_tls: bool = False,
        model: str | None = None,
        tunnel_subnet: str | None = None,
    ) -> UUID:
        """Yangi NVR qurilmasini yozadi va `id` sini qaytaradi.

        ⚠ `host` bu yerda TEKSHIRILMAYDI — `assert_private_host()` API
          chegarasida chaqiriladi (03-07). Repozitoriy validatsiya joyi
          emas: u chaqirilmasdan ham ishlatilishi mumkin (migratsiya,
          seed, fon jarayoni) va u holda tekshiruv jimgina o'tkazib
          yuborilardi. Chegara KIRISHDA turishi kerak.
        """
        result = await self.session.execute(
            insert(NvrDevice)
            .values(
                market_id=self.market_id,
                host=host,
                port=port,
                use_tls=use_tls,
                username=username,
                model=model,
                tunnel_subnet=tunnel_subnet,
            )
            .returning(NvrDevice.id)
        )
        return result.scalar_one()

    async def get_device(self, nvr_id: UUID) -> NvrDevice | None:
        """Bitta qurilma yoki `None`."""
        result = await self.session.execute(
            self.scoped(select(NvrDevice)).where(NvrDevice.id == nvr_id)
        )
        return result.scalar_one_or_none()

    async def list_devices(self) -> Sequence[NvrDevice]:
        """Bozorning barcha NVR qurilmalari (yaratilish tartibida)."""
        result = await self.session.execute(
            self.scoped(select(NvrDevice)).order_by(NvrDevice.created_at, NvrDevice.id)
        )
        return result.scalars().all()

    async def update_device(self, nvr_id: UUID, **values: Any) -> bool:
        """Qurilmaning berilgan maydonlarini yangilaydi.

        Kashfiyot `rtsp_port`, `rtsp_port_assumed`, `serial_number`,
        `firmware_version`, `model`, `device_type` va `last_discovery_at`
        ni shu yo'l bilan yozadi.

        Returns:
            Qator topilgan va yangilangan bo'lsa `True`.
        """
        if not values:
            return False
        result = await self.session.execute(
            update(NvrDevice)
            .where(NvrDevice.market_id == self.market_id, NvrDevice.id == nvr_id)
            .values(**values)
            .returning(NvrDevice.id)
        )
        return result.scalar_one_or_none() is not None

    # ------------------------------------------------------------------
    # Rekvizitlar — FAQAT `bytes` (modul docstringi)
    # ------------------------------------------------------------------

    async def put_credential(self, nvr_id: UUID, encrypted: bytes, key_version: int) -> None:
        """Shifrlangan parolni yozadi yoki almashtiradi.

        `ON CONFLICT (nvr_id)` — jadval 1:1 (PK `nvr_id`), ya'ni «parolni
        yangilash» oqimi ALOHIDA `UPDATE` talab qilmaydi va «avval
        tekshir, keyin yoz» poygasi yo'q.

        Args:
            encrypted: Fernet TOKENI. Ochiq matn parol bu yerga hech
                qachon kelmaydi (modul docstringi).
            key_version: `secrets.CURRENT_KEY_VERSION` — rotatsiyaning ish
                ro'yxatini so'rov bilan topish uchun.
        """
        statement = insert(NvrCredential).values(
            market_id=self.market_id,
            nvr_id=nvr_id,
            password_encrypted=encrypted,
            key_version=key_version,
        )
        await self.session.execute(
            statement.on_conflict_do_update(
                index_elements=[NvrCredential.nvr_id],
                set_={
                    "password_encrypted": statement.excluded.password_encrypted,
                    "key_version": statement.excluded.key_version,
                    "updated_at": datetime.now(tz=UTC),
                },
            )
        )

    async def devices_with_credentials(self) -> frozenset[UUID]:
        """Paroli SAQLANGAN qurilmalarning `id` lari — BITTA so'rov bilan.

        ⚠ SHIFRMATN UMUMAN O'QILMAYDI: so'rov faqat `nvr_id` ustunini
          tanlaydi. `has_password` bayrog'i uchun tokenning O'ZI kerak
          emas va uni tarmoqdan olib kelish sirni keraksiz joyga —
          ilova xotirasiga — chiqarardi.

        ⚠ NEGA RO'YXAT UCHUN ALOHIDA METOD: har qurilma uchun
          `get_credential()` chaqirish N+1 hosil qilardi. Bir bozorda
          NVR soni kichik (Karmanada bitta), lekin naqsh 4-fazaga meros
          bo'lib o'tardi va u yerda kameralar soni yuzlab bo'ladi.
        """
        result = await self.session.execute(self.scoped(select(NvrCredential.nvr_id)))
        return frozenset(result.scalars().all())

    async def get_credential(self, nvr_id: UUID) -> bytes | None:
        """Shifrlangan parol yoki `None`.

        Qaytadigan qiymat — TOKEN. Deshifrlash chaqiruvchining ishi
        (`app/security/secrets.py::decrypt_nvr_password`).
        """
        result = await self.session.execute(
            self.scoped(select(NvrCredential.password_encrypted)).where(
                NvrCredential.nvr_id == nvr_id
            )
        )
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Kameralar — SC#2 ning yuragi
    # ------------------------------------------------------------------

    async def upsert_cameras(
        self,
        nvr_id: UUID,
        run_started_at: datetime,
        channels: Sequence[DiscoveredChannel],
    ) -> UpsertCounts:
        """Kashf etilgan kanallarni IDEMPOTENT yozadi (SC#2).

        `ON CONFLICT (market_id, nvr_id, channel_no) DO UPDATE` va uning
        `SET` ifodasi UCH QAT'IY QOIDANI o'z ichiga oladi:

        1. **`name` faqat `name_overridden = false` bo'lganda yangilanadi.**
           Admin kamerani «Sabzavot qatori» deb nomlaganda keyingi skan uni
           NVR'dagi «Camera 03» ga QAYTARIB QO'YMASLIGI kerak. Bu SC#2 ning
           «mavjudi tegilmaydi» qismi va u `CASE WHEN` ifodasida, DB ichida
           yashaydi — ilova qatlamiga chiqarilsa ikki parallel skanda poyga
           berardi (T-03-26).

        2. **`first_seen_at` `SET` ro'yxatida UMUMAN YO'Q.** Kanal birinchi
           marta qachon ko'rilgani — o'zgarmas fakt. Uni yangilash audit va
           diagnostikani buzardi («kamera qachon paydo bo'ldi?» savoliga
           har skandan keyin yangi javob chiqardi).

        3. **`is_archived` ham `SET` ro'yxatida YO'Q.** Admin arxivlagan
           kanal qayta skanda TIKLANMAYDI — `name_overridden` bilan aynan
           bir xil semantika: kashfiyot NVR ni haqiqat manbai deb biladi,
           lekin ADMIN QARORI undan ustun (D-10).

        `stream_name` ham `SET` da yo'q: u kamera bilan bir marta
        tug'iladi va go2rtc konfiguratsiyasi unga tayanadi. Yangilansa
        jonli ko'rish har skandan keyin uzilardi.

        ⚠ `last_seen_at` `now()` EMAS, `run_started_at`.
          `now()` tranzaksiyaning BOSHLANISH vaqtini beradi, ya'ni u
          `run_started_at` ga teng yoki undan keyin bo'lishi mumkin va
          `mark_missing_offline()` ning `last_seen_at < run_started_at`
          taqqoslashi CHEGARADA noaniq bo'lardi (ko'rilgan kanal
          «yo'qolgan» deb belgilanishi mumkin edi). Bitta aniq vaqt
          tamg'asi ikkala qadamni ham bir ma'noli qiladi.

        `channels_added` `RETURNING (xmax = 0)` bilan hisoblanadi —
        Postgres ning o'z belgisi: `ON CONFLICT` yo'lida yangilangan
        qatorda `xmax` nolga teng emas. Muqobil («avval mavjud
        `channel_no` to'plamini o'qish») IKKI PARALLEL skanda noto'g'ri
        son berardi: ikkalasi ham bo'sh holatni ko'rib, ikkalasi ham
        «hammasi yangi» deb hisoblardi. Bu yerdagi belgi esa qatorning
        HAQIQATDA nima bo'lganini aytadi.

        Args:
            nvr_id: qurilma.
            run_started_at: shu skanning yagona vaqt tamg'asi.
            channels: kashf etilgan kanallar.

        Returns:
            `channels_marked_offline = 0` bo'lgan `UpsertCounts` —
            uchinchi son `mark_missing_offline()` dan keladi.
        """
        if not channels:
            return UpsertCounts(channels_found=0, channels_added=0)

        statement = insert(Camera).values(
            [
                {
                    # `market_id` REPOZITORIYDAN, kanal ma'lumotidan EMAS
                    # (mass-assignment darvozasi — `import_repo.py` bilan
                    # bir xil qoida).
                    "market_id": self.market_id,
                    "nvr_id": nvr_id,
                    "channel_no": channel.channel_no,
                    "stream_name": new_stream_name(),
                    "name": channel.name,
                    "status": channel.status,
                    "source_ip": channel.source_ip,
                    "source_model": channel.source_model,
                    "has_substream": channel.has_substream,
                    "first_seen_at": run_started_at,
                    "last_seen_at": run_started_at,
                }
                for channel in channels
            ]
        )
        upsert = statement.on_conflict_do_update(
            constraint="uq_cameras_market_id_nvr_id_channel_no",
            set_={
                "last_seen_at": run_started_at,
                "status": statement.excluded.status,
                "source_ip": statement.excluded.source_ip,
                "source_model": statement.excluded.source_model,
                "has_substream": statement.excluded.has_substream,
                # 1-QOIDA: admin qo'ygan nom saqlanadi.
                "name": _keep_overridden_name(statement),
            },
            # `first_seen_at`, `is_archived`, `stream_name` ATAYIN YO'Q
            # (docstringdagi 2- va 3-qoidalar).
        )

        # `(xmax = 0)` — Postgres ning O'Z belgisi: `ON CONFLICT` yo'lida
        # YANGILANGAN qatorda `xmax` nolga teng bo'lmaydi. `literal_column`
        # `Result[Any]` beradi, shuning uchun bayroq aniq `bool` ga
        # keltiriladi — `sum()` ni `Any` ustidan sanashdan ko'ra qoida
        # ko'rinadigan bo'lsin.
        result = await self.session.execute(
            upsert.returning(literal_column("(xmax = 0)", Boolean).label("inserted"))
        )
        inserted_flags = [bool(flag) for flag in result.scalars().all()]
        return UpsertCounts(
            channels_found=len(channels),
            channels_added=sum(inserted_flags),
        )

    async def mark_missing_offline(self, nvr_id: UUID, run_started_at: datetime) -> int:
        """Shu skanda KO'RINMAGAN kanallarni `offline` deb belgilaydi.

        ⚠ QATTIQ O'CHIRISH YO'Q va bu taqiq modul docstringida sababi
          bilan yozilgan. Qator QOLADI, faqat `status` o'zgaradi.

        `status <> 'offline'` sharti ATAYIN: usiz allaqachon oflayn
        kanallar har skanda qayta yozilardi va `audit_log` ga hech nima
        aytmaydigan qator tushardi. (Trigger o'zgarishsiz `UPDATE` ni
        o'tkazib yuboradi, lekin so'rov baribir barcha qatorlarni
        qulflardi.)

        Returns:
            Holati o'zgargan kanallar soni — `nvr_discovery_runs.
            channels_marked_offline` ga yoziladi.
        """
        result = await self.session.execute(
            update(Camera)
            .where(
                Camera.market_id == self.market_id,
                Camera.nvr_id == nvr_id,
                Camera.last_seen_at < run_started_at,
                Camera.status != CameraStatus.OFFLINE.value,
            )
            .values(status=CameraStatus.OFFLINE.value)
            .returning(Camera.id)
        )
        return len(list(result.scalars().all()))

    async def list_cameras(
        self, nvr_id: UUID | None = None, *, include_archived: bool = False
    ) -> Sequence[Camera]:
        """Bozorning kameralari (standart holda arxivlanganlarsiz).

        `include_archived` ATAYIN standart bo'yicha `False`: arxivlangan
        kanal admin uchun «yo'q» degani va uni ro'yxatga qo'shish D-10
        ning soft-delete'ini foydalanuvchi uchun ma'nosiz qilardi.
        """
        statement = self.scoped(select(Camera))
        if nvr_id is not None:
            statement = statement.where(Camera.nvr_id == nvr_id)
        if not include_archived:
            statement = statement.where(Camera.is_archived.is_(False))
        result = await self.session.execute(statement.order_by(Camera.channel_no))
        return result.scalars().all()

    async def rename_camera(self, camera_id: UUID, name: str) -> bool:
        """Kamerani qayta nomlaydi va `name_overridden` ni BIRGA qo'yadi.

        ⚠ Ikkala ustun BIR operatorda yoziladi. Ajratilsa (avval nom,
          keyin bayroq) oradagi skan nomni bosib ketardi — va bu aynan
          SC#2 ning buzilishi bo'lardi.
        """
        result = await self.session.execute(
            update(Camera)
            .where(Camera.market_id == self.market_id, Camera.id == camera_id)
            .values(name=name, name_overridden=True)
            .returning(Camera.id)
        )
        return result.scalar_one_or_none() is not None

    async def reset_camera_name(self, camera_id: UUID) -> bool:
        """«NVR qurilmasidagi nomga qaytarish» (UI-SPEC §6.5).

        Faqat bayroqni tushiradi — nomning O'ZI keyingi skanda NVR dagi
        qiymatga qaytadi. Nomni shu yerda tiklashga urinish mumkin emas:
        NVR dagi joriy nom bizda saqlanmaydi (u `name` ustunining o'zi
        edi va u qayta yozilgan).
        """
        result = await self.session.execute(
            update(Camera)
            .where(Camera.market_id == self.market_id, Camera.id == camera_id)
            .values(name_overridden=False)
            .returning(Camera.id)
        )
        return result.scalar_one_or_none() is not None

    async def archive_camera(self, camera_id: UUID) -> bool:
        """Kamerani arxivlaydi (D-10 soft-delete). Qator QOLADI."""
        return await self._set_archived(camera_id, archived=True)

    async def restore_camera(self, camera_id: UUID) -> bool:
        """Arxivdan qaytaradi — bu FAQAT ADMIN qila oladigan amal.

        Qayta skan arxivlangan kanalni TIKLAMAYDI (`upsert_cameras`
        docstringidagi 3-qoida), ya'ni bu yagona qaytish yo'li.
        """
        return await self._set_archived(camera_id, archived=False)

    async def _set_archived(self, camera_id: UUID, *, archived: bool) -> bool:
        result = await self.session.execute(
            update(Camera)
            .where(Camera.market_id == self.market_id, Camera.id == camera_id)
            .values(is_archived=archived)
            .returning(Camera.id)
        )
        return result.scalar_one_or_none() is not None

    # ------------------------------------------------------------------
    # Kashfiyot yugurishlari
    # ------------------------------------------------------------------

    async def create_run(self, nvr_id: UUID, triggered_by: UUID | None = None) -> UUID:
        """Yangi kashfiyot yugurishini `queued` holatida yozadi.

        ⚠ «Faol yugurish bormi?» TEKSHIRILMAYDI — bu ataylab.
          `0012` dagi QISMAN UNIQUE indeks (`status IN ('queued','running')`)
          ikkinchi faol yugurishni `23505` bilan rad etadi va chaqiruvchi
          uni 409 ga aylantiradi (03-06). Oldindan tekshirish «tekshir-
          keyin-yoz» poygasini tug'dirardi: ikki so'rov bir vaqtda bo'sh
          holatni ko'rib, ikkalasi ham skan boshlardi — NVR ga ikki
          barobar yuk va ikki barobar `401` urinishi, ya'ni Hikvision
          hisobining qulflanishi (T-03-16).

        Raises:
            IntegrityError: shu NVR uchun allaqachon faol yugurish bo'lsa
                (SQLSTATE `23505`).
        """
        result = await self.session.execute(
            insert(NvrDiscoveryRun)
            .values(
                market_id=self.market_id,
                nvr_id=nvr_id,
                status=DiscoveryRunStatus.QUEUED.value,
                triggered_by=triggered_by,
            )
            .returning(NvrDiscoveryRun.id)
        )
        return result.scalar_one()

    async def start_run(self, run_id: UUID) -> bool:
        """`queued` -> `running`. Boshqa holatdan o'tkazmaydi (03-06).

        ⚠ `status == 'queued'` SHARTI DARVOZA, TOZALIK EMAS. Navbatlar
          vazifani "KAMIDA BIR MARTA" yetkazadi, ya'ni bir xil `run_id`
          bilan ikkinchi chaqiruv MUMKIN. Shartsiz `UPDATE` ikkinchi jobni
          ham ishga tushirardi va NVR ga IKKI BAROBAR Digest urinishi
          borardi — bu esa Hikvision hisobining qulflanishi (T-03-16/D-03).
          Shart bilan esa ikkinchi chaqiruv `False` oladi va jimgina
          chiqib ketadi.

        ⚠ `started_at` QAYTA YOZILMAYDI: u qator yaratilganda (`create_run`,
          ya'ni admin tugmani bosgan payt) qo'yiladi va foydalanuvchi uchun
          "kashfiyot qachon boshlandi" savolining javobi AYNAN o'sha payt —
          navbatda kutish ham kutishdir.

        Returns:
            Qator `queued` holatda topilgan va `running` ga o'tgan bo'lsa
            `True`. `False` — qator yo'q, boshqa holatda yoki (tenant
            konteksti o'rnatilmagan bo'lsa) RLS uni ko'rsatmadi.
        """
        result = await self.session.execute(
            update(NvrDiscoveryRun)
            .where(
                NvrDiscoveryRun.market_id == self.market_id,
                NvrDiscoveryRun.id == run_id,
                NvrDiscoveryRun.status == DiscoveryRunStatus.QUEUED.value,
            )
            .values(status=DiscoveryRunStatus.RUNNING.value)
            .returning(NvrDiscoveryRun.id)
        )
        return result.scalar_one_or_none() is not None

    async def set_channels_found(self, run_id: UUID, channels_found: int) -> bool:
        """Oraliq yangilanish: kanallar SANAB CHIQILDI (UI-SPEC §5.2 [TALAB]).

        ⚠ NEGA ALOHIDA METOD, `finish_run()` NING BIR QISMI EMAS: bu qiymat
          skan HALI DAVOM ETAYOTGANDA yoziladi va u yugurishning YAKUNI
          emas. `finish_run()` bir vaqtda `finished_at` ni ham qo'yadi,
          ya'ni uni bu yerda ishlatish yugurishni tugagan deb ko'rsatardi
          va poll qilayotgan UI natijani vaqtidan oldin chizardi.

        Chaqiruvchi buni O'Z, QISQA tranzaksiyasida bajaradi — sabab
        `app/jobs/discovery.py` modul docstringida (uzun tranzaksiya ichida
        yozilgan qiymat `COMMIT` gacha hech kimga ko'rinmaydi).

        Returns:
            Qator topilgan bo'lsa `True`.
        """
        result = await self.session.execute(
            update(NvrDiscoveryRun)
            .where(
                NvrDiscoveryRun.market_id == self.market_id,
                NvrDiscoveryRun.id == run_id,
            )
            .values(channels_found=channels_found)
            .returning(NvrDiscoveryRun.id)
        )
        return result.scalar_one_or_none() is not None

    async def finish_run(
        self,
        run_id: UUID,
        status: str,
        counts: UpsertCounts | None = None,
        error_code: str | None = None,
        error_detail: dict[str, Any] | None = None,
    ) -> bool:
        """Yugurishni yakunlaydi: holat, sonlar va (bo'lsa) xato.

        ⚠ `error_detail` YOZISHDAN OLDIN `mask_sensitive()` DAN O'TADI
          (§S-7, T-03-28). Bu jsonb'ga XOM ISAPI javobi tushadi va unda
          rekvizit qoldig'i bo'lishi mumkin. Filtr FAQAT kalit nomiga
          qaraydi (`logging.py` bilan bir xil chuqurlikda, ichma-ich
          obyektlarni ham qamraydi), ya'ni parol bu yerga NOMLANGAN kalit
          sifatida tushishi shart — formatlangan matn ichida hech qachon.

        `finished_at` DB da `now()` bilan emas, shu operatorda yoziladi.
        """
        values: dict[str, Any] = {
            "status": status,
            "finished_at": datetime.now(tz=UTC),
            "error_code": error_code,
            "error_detail": mask_sensitive(error_detail) if error_detail is not None else None,
        }
        if counts is not None:
            values["channels_found"] = counts.channels_found
            values["channels_added"] = counts.channels_added
            values["channels_marked_offline"] = counts.channels_marked_offline

        result = await self.session.execute(
            update(NvrDiscoveryRun)
            .where(
                NvrDiscoveryRun.market_id == self.market_id,
                NvrDiscoveryRun.id == run_id,
            )
            .values(**values)
            .returning(NvrDiscoveryRun.id)
        )
        return result.scalar_one_or_none() is not None

    async def get_run(self, run_id: UUID) -> NvrDiscoveryRun | None:
        """Bitta yugurish yoki `None` (frontend `id` bo'yicha poll qiladi)."""
        result = await self.session.execute(
            self.scoped(select(NvrDiscoveryRun)).where(NvrDiscoveryRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def active_run_id(self, nvr_id: UUID) -> UUID | None:
        """Shu NVR dagi FAOL yugurishning `id` si yoki `None`.

        Qisman UNIQUE indeks tufayli natija KO'PI BILAN bitta bo'ladi —
        `scalar_one_or_none()` shuning uchun to'g'ri va u indeks
        buzilganda JIMGINA birinchi qatorni olib qo'ymaydi.
        """
        result = await self.session.execute(
            self.scoped(select(NvrDiscoveryRun.id)).where(
                NvrDiscoveryRun.nvr_id == nvr_id,
                NvrDiscoveryRun.status.in_(ACTIVE_RUN_STATUSES),
            )
        )
        return result.scalar_one_or_none()


def _keep_overridden_name(statement: Insert) -> Case[str]:
    """`CASE WHEN cameras.name_overridden THEN cameras.name ELSE EXCLUDED.name END`.

    Alohida funksiyaga chiqarilgan, chunki u `upsert_cameras` ning eng
    muhim va eng oson buziladigan bandi: `EXCLUDED.name` ga
    soddalashtirish butun SC#2 ni jimgina o'chirardi va bironta sxema
    testi buni ko'rmasdi (`test_nvr_repo.py` dagi sabotaj shuni
    o'lchaydi).
    """
    return case(
        (Camera.name_overridden, Camera.name),
        else_=statement.excluded.name,
    )
