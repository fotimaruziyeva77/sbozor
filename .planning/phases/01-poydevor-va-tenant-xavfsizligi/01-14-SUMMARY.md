---
phase: 01-poydevor-va-tenant-xavfsizligi
plan: 14
subsystem: database
tags: [postgres, rls, security-definer, audit, alembic, alembic-utils, gap-closure]

# Dependency graph
requires:
  - phase: "01-04"
    provides: "`owner_bootstrap_policy()` naqshi, `SECURITY DEFINER` + `search_path` pin qolipi, `entity_types=[PGPolicy, PGFunction]` filtri, `ALL_ENTITIES` reyestri"
  - phase: "01-05"
    provides: "`audit_log` jadvali, `audit_read`/`audit_append` policy'lari, o'zgarmaslikning 4 qatlami, `ix_audit_log_market_id_at` indeksi"
  - phase: "01-06"
    provides: "`login_failed` yozuvi (`market_id=NULL`, `source='app'`) — bu reja ochadigan qatorlarning manbai"
provides:
  - "`audit_read_platform` policy — `FOR SELECT TO sbozor_owner USING (market_id IS NULL)`"
  - "`auth_list_platform_audit(integer, timestamptz, bigint)` — SECURITY DEFINER, keyset sahifalash bilan"
  - "`PLATFORM_AUDIT_FUNCTIONS` / `PLATFORM_AUDIT_GRANT_SIGNATURES` eksportlari"
  - "`0005_platform_audit` migratsiyasi (sxemani o'zgartirmaydi)"
  - "5 ta yangi test: 1 meta (owner-only qulf) + 4 funksional (Gap 5 uchdan-uchiga)"
affects:
  - "01-15 (API: `GET /api/v1/audit/platform` aynan shu funksiya ustiga quriladi)"
  - "kelajakdagi audit ekranlari (platforma-global hodisalar endi mahsulot yo'lidan o'qiladi)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "FORCE RLS ostidagi jadvalda `SECURITY DEFINER` YOLG'IZ YETMAYDI — u owner-scoped policy bilan JUFTLIKDA ishlaydi"
    - "Owner uchun ochiladigan policy komandasi eng tor bo'lishi shart: `FOR SELECT`, `FOR ALL` emas (o'zgarmaslik qatlami saqlanadi)"
    - "DB funksiyasidagi `LIMIT` fail-closed: `LIMIT COALESCE(p_limit, 0)` — `LIMIT NULL` cheklovsiz degani"
    - "Keyset chegarasi DB funksiyasida ham `(at, id)` JUFTLIGI — `audit_repo` bilan bitta semantika"

key-files:
  created:
    - migrations/versions/0005_platform_audit.py
  modified:
    - migrations/entities/policies.py
    - migrations/entities/functions.py
    - migrations/entities/__init__.py
    - tests/tenancy/test_meta.py
    - tests/tenancy/test_login_bootstrap.py

key-decisions:
  - "`audit_read_platform` — `TO sbozor_owner` va `FOR SELECT`: haqiqiy chegara `sbozor_app`, o'zgarmaslikning 2-qatlami esa tegilmaydi"
  - "`owner_bootstrap` policy'si `audit_log` ga HAMON berilmaydi — yangi policy uning o'rnini bosmaydi, chunki komandasi tor"
  - "`LIMIT COALESCE(p_limit, 0)` (rejadagi xom `LIMIT p_limit` o'rniga) — `None` bitta so'rovda butun jurnalni tortib olmasin"
  - "`ip` ustuni funksiya chiqishida YO'Q — mavjud `AuditEntry` shaklidan kengroq ma'lumot berilmaydi"
  - "Funksiya ixtiyoriy `WHERE` qabul qilmaydi — sharti LITERAL `market_id IS NULL`, ya'ni tenant qatorlari undan HECH QACHON qaytmaydi"
  - "Meta-testdagi policy to'plami kengaytirildi, ASSERT YUMSHATILMADI — uchinchi policy aniq nomi bilan yozildi"

patterns-established:
  - "Pattern: yangi policy qo'shilganda `test_audit_read_policy_is_tenant_scoped` dagi to'plam ATAYIN qo'lda kengaytiriladi (yumshatilmaydi) — `w`/`d` paydo bo'lishi baribir qizaradi"
  - "Pattern: policy+funksiya juftligi SABOTAJ bilan sinaladi — policy olib tashlanganda funksiya 0 qator berishi o'lchanadi, taxmin qilinmaydi"
  - "Pattern: DB funksiyasining har bir NULL-kirish yo'li fail-closed bo'lishi va test bilan qulflanishi shart (`p_limit`, yarim kursor)"

requirements-completed: [FOUND-03]

# Metrics
duration: 40min
completed: 2026-07-29
---

# Phase 1 Plan 14: Platforma-global audit o'qish yo'li (Gap 5 — DB qatlami) Summary

**`audit_read_platform` owner-scoped `FOR SELECT` policy'si va u bilan juftlikda ishlaydigan `auth_list_platform_audit()` SECURITY DEFINER funksiyasi — `login_failed` kabi `market_id IS NULL` audit qatorlari endi mahsulot yo'lidan o'qiladi, `sbozor_app` uchun esa to'g'ridan-to'g'ri yo'l yopiq qoladi.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-07-29T19:14:00Z
- **Completed:** 2026-07-29T19:54:00Z
- **Tasks:** 2/2
- **Files created:** 1 (modifikatsiya: 5)
- **Tests:** 380 yashil (oldin 375; +1 meta, +4 funksional)

## Accomplishments

- **Uch marta ketma-ket qayd etilgan bo'shliq DB tomonda yopildi.** 01-06, 01-07 va 01-09 SUMMARY'lari `market_id IS NULL` audit qatorlarini "o'qish yo'li yo'q" deb qoldirgan edi, chunki har bir rejaning `<interfaces>` bo'limi `GET /audit` ni tenant-scoped deb e'lon qilgan. Endi bu qatorlar `auth_list_platform_audit()` orqali o'qiladi — FOUND-03 ning "kim tizimga kirishga urinmoqda" savoli javobli bo'ldi.

- **Rejaning eng muhim arxitektura da'vosi O'LCHANDI, taxmin qilinmadi.** Reja "`SECURITY DEFINER` yolg'iz yetmaydi, chunki `audit_log` da FORCE RLS va `sbozor_owner` NOBYPASSRLS" deb yozgan edi. Bu sabotaj bilan tekshirildi: `0005` dan `create_entity(audit_read_platform_policy())` olib tashlanganda funksiya AYNAN 0 qator qaytardi (`assert 0 == 1`), policy qaytarilgach yana yashil. Ya'ni juftlik haqiqiy — bu ikkita mustaqil obyekt emas, bitta mexanizmning ikki yarmi.

- **App-rol yuzasi KENGAYMAGANI alohida test bilan isbotlandi.** `test_platform_audit_rows_are_invisible_to_app_role_directly`: ilova roli o'zi yozgan `market_id IS NULL` qatorni darhol keyin `SELECT ... WHERE market_id IS NULL` bilan o'qiy olmaydi — 0 qator. Ya'ni policy `TO sbozor_owner` ekani nazariy emas, o'lchangan chegara: funksiya-darvoza chetlab o'tilmaydi.

- **O'zgarmaslik zanjiri tegilmadi.** Yangi policy `FOR SELECT`, ya'ni `audit_log` da `UPDATE`/`DELETE` uchun baribir birorta policy yo'q. `tests/integration/test_audit_immutable.py` ning 4 qatlami o'zgarishsiz yashil, meta-test esa endi uchta policy'ni AYNAN nomi va komandasi bilan qulflaydi (`{audit_append: a, audit_read: r, audit_read_platform: r}`) — `w` yoki `d` paydo bo'lishi hamon darhol qizaradi.

- **Model ↔ migratsiya pariteti saqlandi.** `downgrade -1` → `upgrade head` → `downgrade base` → `upgrade head` zanjiri xatosiz; `alembic revision --autogenerate` BO'SH diff beradi, ya'ni ikkala yangi entity `ALL_ENTITIES` da to'g'ri ro'yxatga olingan va `entity_types=[PGPolicy, PGFunction]` filtri buzilmagan.

## Task Commits

1. **Task 1: `audit_read_platform` policy + `auth_list_platform_audit` funksiyasini aniqlash** — `93ca25d` (feat)
2. **Task 2: 0005 migratsiya + meta-test/grant darvozalarini yangilash** — `820ae36` (feat)

## Files Created/Modified

**Migratsiya qatlami**

- `migrations/entities/policies.py` — `AUDIT_READ_PLATFORM_SIGNATURE`, `PLATFORM_AUDIT_PREDICATE` konstantalari va `audit_read_platform_policy()` fabrikasi. Docstringda uch savol alohida javoblangan: nega umuman kerak (Gap 5), nega yolg'iz `SECURITY DEFINER` yetmaydi (FORCE + NOBYPASSRLS), nega `TO sbozor_owner` va nega `FOR SELECT`.
- `migrations/entities/functions.py` — `AUTH_LIST_PLATFORM_AUDIT` (`SECURITY DEFINER`, `SET search_path = pg_catalog, public`, `STABLE`, 13 ustunli `RETURNS TABLE`), `PLATFORM_AUDIT_FUNCTIONS`, `PLATFORM_AUDIT_GRANT_SIGNATURES`. Bo'lim izohida bu funksiyaning oldingilardan farqi yozilgan: u RLS QO'YILGAN jadvalni o'qiydi, `users` esa RLS'siz — shuning uchun naqsh ham boshqacha.
- `migrations/entities/__init__.py` — ikkala entity `ALL_ENTITIES` da; `RLS_TABLES` docstringiga "`audit_read_platform` bunga zid emas, chunki `FOR SELECT`" izohi qo'shildi.
- `migrations/versions/0005_platform_audit.py` — policy → funksiya → `REVOKE ALL FROM PUBLIC` + `GRANT EXECUTE TO sbozor_app`; `downgrade()` teskari tartibda. Sarlavha izohida "nega ikki obyekt, bittasi emas" jadvali.

**Testlar**

| Fayl | Yangi test | Nima qulflanadi |
| ---- | ---------- | --------------- |
| `test_meta.py` | `test_audit_read_platform_is_owner_only` | rollar AYNAN `{sbozor_owner}`, komanda AYNAN `SELECT`, predikat AYNAN `(market_id IS NULL)` — uchtasi ham `pg_policies` dan |
| `test_login_bootstrap.py` | `test_platform_audit_rows_are_invisible_to_app_role_directly` | app-rol NULL qatorlarni to'g'ridan-to'g'ri KO'RMAYDI |
| `test_login_bootstrap.py` | `test_auth_list_platform_audit_returns_null_market_rows` | funksiya o'sha qatorni QAYTARADI (Gap 5 ning yopilishi) |
| `test_login_bootstrap.py` | `test_auth_list_platform_audit_keyset_excludes_boundary_row` | kursor qat'iy `<` — chegara qatori takrorlanmaydi |
| `test_login_bootstrap.py` | `test_auth_list_platform_audit_without_limit_returns_nothing` | `p_limit IS NULL` → 0 qator (fail-closed) |

Bundan tashqari `test_meta.py` dagi `EXPECTED_DEFINER_FUNCTIONS` va `test_audit_read_policy_is_tenant_scoped` kutilgan to'plami kengaytirildi, `test_login_bootstrap.py` dagi `DEFINER_FUNCTION_SETS` ga to'rtinchi juftlik qo'shildi (grant + PUBLIC darvozalari yangi funksiyani AVTOMATIK qamrab oldi).

## Decisions Made

- **`FOR SELECT`, `FOR ALL` EMAS — bu qarorning butun og'irligi shu yerda.** `owner_bootstrap` policy'si `audit_log` ga ATAYIN berilmagan edi (01-05), chunki `FOR ALL ... USING (true)` egaga `UPDATE`/`DELETE` da qatorlarni ko'rsatib qo'yardi. Yangi policy o'sha qarorni bekor QILMAYDI: u ham egaga mo'ljallangan, lekin komandasi tor va predikati tor. Farq faqat ikki so'zda, shuning uchun meta-test komandani `SELECT` ga qulfladi — kelajakda kimdir uni "soddalashtirsa" CI darhol qizaradi.

- **`TO sbozor_owner` — haqiqiy chegara `sbozor_app` bo'lgani uchun.** 01-04 dagi `owner_bootstrap` bilan bir xil mantiq: `sbozor_owner` jadvalning EGASI, u xohlagan payt `ALTER TABLE ... NO FORCE` qila oladi, ya'ni FORCE unga qarshi hech qachon xavfsizlik nazorati bo'lmagan. Ilova esa FAQAT `sbozor_app` bilan ulanadi va bu policy unga UMUMAN qo'llanmaydi — ya'ni NULL qatorlarga yagona yo'l grant qilingan funksiya bo'lib qoladi va yuza greplanadigan.

- **`ip` ustuni funksiya chiqishida yo'q.** `app.api.v1.audit.AuditEntry` uni ham qaytarmaydi (D-12 maskalash qarori). Uni "har ehtimolga qarshi" qo'shish 01-15 dagi endpointga mavjud tenant-scoped o'qishdan KENGROQ ma'lumot berish yo'lini ochardi.

- **Funksiya ixtiyoriy `WHERE` qabul qilmaydi.** Sharti LITERAL `market_id IS NULL`, ya'ni uni "RLS'siz butun audit jurnalini o'qish" vositasiga aylantirib bo'lmaydi: `market_id` to'ldirilgan qatorlar undan HECH QACHON qaytmaydi. Bu 01-04 dagi `auth_list_users(uuid[])` va 01-03 dagi refresh funksiyalari bilan bir xil qoida.

- **Keyset semantikasi `audit_repo.list_audit` dan NUSXA OLINDI, qayta o'ylab topilmadi.** `(at, id)` juftligi, `ORDER BY at DESC, id DESC`, chaqiruvchi `limit + 1` beradi. Ikki joyda ikki xil sahifalash bo'lsa 01-15 dagi endpoint tenant va platforma rejimlarida boshqacha xulq ko'rsatardi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `LIMIT p_limit` → `LIMIT COALESCE(p_limit, 0)`**

- **Found during:** Task 1 (funksiya tanasini yozishda)
- **Issue:** Reja `LIMIT p_limit` deb yozgan. Postgres uchun `LIMIT NULL` "CHEKLOVSIZ" degani, ya'ni chaqiruvchida bitta `None` (masalan 01-15 dagi sahifalash bug'i yoki validatsiyasiz parametr) butun platforma-global audit jurnalini BIR so'rovda tortib olardi — o'sish cheklanmagan, append-only jadvalda bu vaqt o'tgan sari yomonlashadi. Bu resurs sarfi va shu bilan birga ma'lumot yuzasi masalasi.
- **Fix:** `LIMIT COALESCE(p_limit, 0)` — noto'g'ri kirish XATO emas, 0 QATOR beradi. Bu loyihaning mavjud fail-closed qoidasi bilan bir xil (`NULLIF(current_setting(...), '')` RLS predikatida). Musbat `p_limit` uchun xulq rejadagidan hech qanday farq qilmaydi, ya'ni 01-15 uchun mos.
- **Files modified:** `migrations/entities/functions.py`
- **Verification:** `test_auth_list_platform_audit_without_limit_returns_nothing` — `auth_list_platform_audit(NULL, NULL, NULL)` bo'sh ro'yxat qaytaradi
- **Committed in:** `93ca25d` (Task 1 commit)

### Kichik moslashtirishlar (xato emas, tanlov)

- **`PLATFORM_AUDIT_PREDICATE` konstantasi qo'shildi** (rejada aniq talab qilinmagan): `TENANT_PREDICATE`/`MARKETS_PREDICATE` bilan bir xil joyda tursin va nega u tenant predikatining ALTERNATIVASI emas, TO'LDIRUVCHISI ekani bir marta yozilsin (ikkalasi kesishmaydi).
- **`audit_read_policy()` docstringidagi eskirgan havola tuzatildi.** Unda "ular platforma admini uchun alohida tor yo'l bilan beriladi (01-07)" deb turardi — 01-07 bu ishni bajarmagan (aynan shu Gap 5). Havola endi `audit_read_platform_policy()` + `auth_list_platform_audit()` (0005) ga ishora qiladi. DDL ta'rifi o'zgarmagani uchun autogenerate ta'sirlanmadi.
- **Rejada bitta funksional test so'ralgan edi, to'rtta yozildi.** Reja "(i) funksiya qatorni qaytaradi, (ii) to'g'ridan-to'g'ri SELECT 0 beradi" deb bitta testda ikkita da'voni birlashtirgan. Ular alohida testlarga ajratildi (yiqilganda qaysi yarmi buzilgani darhol ko'rinadi), ustiga keyset chegarasi va `p_limit IS NULL` fail-closed qulflari qo'shildi — ikkinchisi yuqoridagi Rule 2 tuzatishining isboti.
- **`test_audit_read_platform_is_owner_only` predikatni ham tekshiradi** (reja rollar va komandani so'ragan edi): predikat `true` ga kengayishi policy'ni butun jurnalga ochib yuborardi va bu boshqa hech qaysi test ko'rmaydigan yagona buzilish yo'li edi.

---

**Total deviations:** 1 auto-fixed (1× Rule 2 — `LIMIT NULL` cheklovsizligi).
**Impact on plan:** Scope creep yo'q. Rejaning barcha qabul mezonlari o'zgarishsiz bajarildi; yagona tuzatish rejadagi SQL bandining bitta Postgres semantikasini fail-closed qildi va uning o'zi test bilan qoplandi.

## Issues Encountered

- **`ruff format` bitta assert xabarini bir satrga yig'ishni talab qildi** — ikki qismli satr birlashtirilib qayta formatlandi, mazmun o'zgarmadi.
- **Migratsiya round-trip va autogenerate tekshiruvi uchun `.env` kerak bo'lmadi.** `compose --profile migrate` o'rniga vaqtinchalik pytest fayli yozildi (`tests/tenancy/test_zz_roundtrip_scratch.py`): u sessiya testcontainer'idagi `owner_url` fixture'ini ishlatib `downgrade -1 → upgrade head → downgrade base → upgrade head` zanjirini bajardi va `command.revision(..., process_revision_directives=...)` bilan autogenerate direktivalarini FAYL YOZMASDAN ushlab oldi (`upgrade_ops.is_empty()`). Bu yondashuv parallel ishlayotgan qo'shni agentlar bilan port/konteyner ziddiyatiga umuman tushmaydi. Fayl tekshiruvdan keyin o'chirildi va commit'ga tushmadi.
- **Qo'shni agentlar bilan compose test profilida ziddiyat kuzatilmadi** — testcontainers har sessiyada tasodifiy portli yangi konteyner ko'taradi.

## Known Stubs

Yo'q. Bu rejadagi policy, funksiya, migratsiya va beshta testning hammasi to'liq ishlaydi va haqiqiy `postgres:18.4-trixie` ga qarshi tekshirilgan.

Atayin **keyingi rejaga** qoldirilgan (stub emas, chegara shunday belgilangan):

- **API endpointi (`GET /api/v1/audit/platform`) — 01-15.** Bu reja ATAYIN faqat DB qatlamini quradi. Funksiya hozir hech qanday mahsulot kodidan chaqirilmaydi, lekin u `sbozor_app` ga grant qilingan va testlar uni ishlatadi, ya'ni u "o'lik kod" emas, tayyor kontrakt.
- **Huquq tekshiruvi (`is_platform_admin`) — 01-15 da, ILOVA qatlamida.** Bu qaror 01-04 dagi `auth_list_markets()` bilan bir xil: DB funksiyasi kim chaqirayotganini bilmaydi, RBAC esa har doim ilova qatlamida (D-07). Funksiyaning `sbozor_app` ga grant qilingani o'z-o'zidan huquq bermaydi — u faqat 01-15 dagi `require_permission(...)` ortidan chaqiriladi.

## Threat Flags

Yangi, reyestrda qayd etilmagan xavfsizlik yuzasi paydo bo'lmadi. Rejadagi uchala dispozitsiya bajarildi:

| Threat | Qanday yopildi | Tekshiruv |
| ------ | -------------- | --------- |
| T-01-88 (Information Disclosure) | Policy `TO sbozor_owner` + `FOR SELECT` + predikat `market_id IS NULL` | `test_audit_read_platform_is_owner_only` (rollar + komanda + predikat), `test_platform_audit_rows_are_invisible_to_app_role_directly` |
| T-01-89 (Elevation of Privilege) | Funksiya ixtiyoriy `WHERE` qabul qilmaydi; `SET search_path = pg_catalog, public`; `REVOKE ALL FROM PUBLIC` + `GRANT EXECUTE TO sbozor_app` | `test_security_definer_functions_pin_search_path`, `test_definer_functions_are_executable_by_app_role`, `test_definer_functions_are_not_granted_to_public` |
| T-01-90 (Tampering — accept/verified) | Yangi policy `FOR SELECT`; `UPDATE`/`DELETE` uchun policy hamon yo'q | `test_audit_read_policy_is_tenant_scoped` (to'plam AYNAN uchta), `test_audit_log_is_read_only_for_app_role`, `tests/integration/test_audit_immutable.py` (o'zgarishsiz yashil) |

## User Setup Required

Yo'q — tashqi servis konfiguratsiyasi talab qilinmaydi. Migratsiya mavjud oqim bilan qo'llanadi:

```
npm run migrate     # docker compose --profile migrate run --rm migrate alembic upgrade head
npm test            # docker compose --profile test run --rm tests pytest -q
```

## Next Phase Readiness

**01-15 uchun tayyor:**

- Funksiya imzosi qat'iy: `auth_list_platform_audit(p_limit integer, p_before_at timestamptz, p_before_id bigint)`.
- Qaytadigan 13 ustun `app.schemas.AuditEntry` maydonlari bilan AYNAN mos (`ip` dan tashqari — u `AuditEntry` da ham yo'q), ya'ni endpoint qatorni to'g'ridan-to'g'ri o'shanga o'girishi mumkin.
- Keyset chaqiruv shakli: birinchi sahifa `(limit + 1, NULL, NULL)`; keyingisi `(limit + 1, oxirgi_at, oxirgi_id)`. `encode_cursor`/`decode_cursor` (`audit_repo`) qayta ishlatiladi — kursor formati bir xil bo'lib qoladi.
- `sbozor_app` funksiyani chaqira oladi va u `PUBLIC` ga berilmagan; grant darvozasi testda avtomatik.

**Ochiq e'tibor nuqtalari:**

- **Funksiya hozircha mahsulot kodidan chaqirilmaydi.** Agar 01-15 biror sababga ko'ra bajarilmasa, `0005` "ishlatilmaydigan yuza" bo'lib qoladi — u tor va grant bilan cheklangan, lekin ochiq gap sifatida qayd etiladi.
- **Huquq tekshiruvi 01-15 ning zimmasida.** `sbozor_app` ga berilgan `EXECUTE` — bu ILOVA chaqira olishi degani, "har qanday foydalanuvchi ko'ra oladi" degani EMAS. 01-15 endpointi `require_permission(...)` ortida bo'lishi SHART, aks holda platforma-global audit har qanday tizimga kirgan foydalanuvchiga ochilib qoladi. Bu 01-04 dagi `auth_list_markets()` bilan aynan bir xil taqsimot (D-06/D-07).
- **`GET /audit/platform` ning O'QILGANI ham auditga yozilishi kerak (D-09).** Mavjud `audit_read(...)` dependency'si tenant-scoped yozadi; platforma rejimida yozuv `market_id=NULL` bilan tushadi va o'sha yozuvni yana shu funksiya qaytaradi — bu kutilgan, lekin 01-15 da ataylab tanlanishi kerak bo'lgan xulq.

## Self-Check: PASSED

- **Fayllar:** da'vo qilingan 6 ta artefaktning (1 yangi + 5 modifikatsiya) hammasi mavjud va git'da kuzatilmoqda; SUMMARY ham joyida.
- **Commitlar:** `93ca25d`, `820ae36` — ikkalasi ham `git log` da mavjud.
- **O'chirilgan fayl yo'q:** `git diff --diff-filter=D --name-only 1f36ae9..HEAD` bo'sh.
- **Rejadan tashqari faylga tegilmadi:** `git diff --name-only 1f36ae9..HEAD` aynan `files_modified` ro'yxatidagi 6 faylni beradi.
- **Umumiy artefaktlarga tegilmadi:** `STATE.md` / `ROADMAP.md` / `REQUIREMENTS.md` diff'da yo'q (worktree rejimi — ularni orkestrator yangilaydi).
- **Ishchi katalog toza:** vaqtinchalik round-trip test fayli o'chirildi, `git status --short` da kuzatilmagan fayl yo'q.
- **Darvozalar:** `ruff check` + `ruff format --check` + `mypy` (strict, 84 fayl) + `pytest` (380 test) — hammasi yashil.
- **Migratsiya:** `downgrade -1 → upgrade head → downgrade base → upgrade head` xatosiz; `alembic revision --autogenerate` BO'SH diff (`upgrade_ops.is_empty()`).
- **Sabotaj:** `create_entity(audit_read_platform_policy())` olib tashlanganda ikkita funksional test 0 qator bilan yiqildi; policy qaytarilgach suite yana yashil.

---
*Phase: 01-poydevor-va-tenant-xavfsizligi*
*Completed: 2026-07-29*
