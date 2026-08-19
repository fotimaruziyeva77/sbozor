-- =============================================================================
-- DEV NAMUNA MA'LUMOTI — PANELNI RAQAM BILAN KO'RISH UCHUN.
--
-- ⛔⛔ BU ISHLAB CHIQARISH SKRIPTI EMAS VA U YERDA ISHLAMAYDI.
--
--     Skript boshida QAT'IY HIMOYA bor: bozor nomida «test» so'zi
--     bo'lmasa, u xato bilan to'xtaydi. Ma'muriyatning haqiqiy
--     raqamlari yoniga to'qilgan to'lov yozish — bu mahsulot oldini
--     olish uchun qurilgan xatoning aynan o'zi bo'lardi.
--
-- NEGA KERAK: direktor paneli Stitch maketi bilan solishtirilganda
-- bizning bazamiz bo'm-bo'sh edi va ekranda hamma joyda «—» turardi.
-- Bo'sh panelda kompozitsiyani (qiymat rangi, yorliq joyi, uzun
-- sonning satrga sig'ishi) BAHOLAB BO'LMAYDI.
--
-- Ishlatish:
--   docker compose exec -T db psql -U postgres -d sbozor -f - < ops/scripts/dev_seed_panel.sql
-- yoki:
--   docker compose exec -T db psql -U postgres -d sbozor < ops/scripts/dev_seed_panel.sql
-- =============================================================================
\set ON_ERROR_STOP on

DO $$
DECLARE
  v_market   uuid;
  v_name     text;
  v_zone_a   uuid;
  v_zone_b   uuid;
  v_cat_food uuid;
  v_cat_wear uuid;
  v_tar_food uuid;
  v_tar_wear uuid;
  v_cashier  uuid;
  v_today    date := (now() AT TIME ZONE 'Asia/Tashkent')::date;
  v_stall    uuid;
  v_vendor   uuid;
  v_cat      uuid;
  v_tariff   uuid;
  v_amount   bigint;
  v_shift    uuid;
  v_paid     bigint := 0;
  i          int;
BEGIN
  SELECT id, name INTO v_market, v_name FROM markets ORDER BY created_at LIMIT 1;
  IF v_market IS NULL THEN
    RAISE EXCEPTION 'Bozor topilmadi';
  END IF;

  -- ⛔⛔ HIMOYA: faqat test bozori. Bu shart OLIB TASHLANMAYDI.
  IF position('test' in lower(v_name)) = 0 THEN
    RAISE EXCEPTION
      'TO''XTATILDI: «%» test bozori emas. Bu skript faqat dev bazasi uchun.',
      v_name;
  END IF;

  SELECT id INTO v_zone_a FROM zones WHERE name = 'Sabzavot qatori';
  SELECT id INTO v_zone_b FROM zones WHERE name = 'Meva qatori';
  SELECT id INTO v_cat_food FROM stall_categories WHERE name = 'Oziq-ovqat';
  SELECT id INTO v_cat_wear FROM stall_categories WHERE name = 'Kiyim-kechak';
  SELECT id INTO v_tar_food FROM tariffs
    WHERE category_id = v_cat_food AND valid_from <= v_today
    ORDER BY valid_from DESC LIMIT 1;
  SELECT id INTO v_tar_wear FROM tariffs
    WHERE category_id = v_cat_wear AND valid_from <= v_today
    ORDER BY valid_from DESC LIMIT 1;
  SELECT id INTO v_cashier FROM users WHERE phone_e164 = '+998901111111';

  -- ---------------------------------------------------------------------
  -- 1. Sotuvchilar — 24 nafar (bittasi allaqachon bor).
  -- ---------------------------------------------------------------------
  FOR i IN 1..24 LOOP
    INSERT INTO vendors (market_id, full_name, phone_e164)
    SELECT v_market,
           (ARRAY['Anvar','Bahodir','Dilnoza','Elyor','Farrux','Gulnora',
                  'Hasan','Iroda','Jasur','Kamola','Lola','Mansur',
                  'Nodira','Otabek','Parvina','Qodir','Rustam','Sabina',
                  'Temur','Umida','Vohid','Xurshid','Yulduz','Zafar'])[i]
           || ' ' ||
           (ARRAY['Karimov','Rasulov','Yo''ldoshev','Toshpo''latov','Aliyev',
                  'Nazarova','Sodiqov','Ergasheva','Qosimov','Hamroyeva',
                  'Sattorov','Nurmatov','Islomova','Jo''rayev','Salimova',
                  'Xolmatov','Umarov','Yusupova','Bekmurodov','Sharipova',
                  'Nazirov','Odilov','Mirzayeva','Ochilov'])[i],
           '+99890' || lpad((7000000 + i)::text, 7, '0')
    WHERE NOT EXISTS (
      SELECT 1 FROM vendors
      WHERE market_id = v_market
        AND phone_e164 = '+99890' || lpad((7000000 + i)::text, 7, '0')
    );
  END LOOP;

  -- ---------------------------------------------------------------------
  -- 2. Rastalar — 40 ta (A-01..A-20 va B-01..B-20).
  -- ---------------------------------------------------------------------
  FOR i IN 1..20 LOOP
    /* `code_sort` — GENERATED ustun, unga qiymat yozilmaydi. */
    INSERT INTO stalls (market_id, zone_id, code, status)
    VALUES (v_market, v_zone_a, 'A-' || lpad(i::text, 2, '0'), 'active')
    ON CONFLICT DO NOTHING;
    INSERT INTO stalls (market_id, zone_id, code, status)
    VALUES (v_market, v_zone_b, 'B-' || lpad(i::text, 2, '0'), 'active')
    ON CONFLICT DO NOTHING;
  END LOOP;

  -- ---------------------------------------------------------------------
  -- 3. Toifa va sotuvchi biriktirish.
  -- ---------------------------------------------------------------------
  i := 0;
  FOR v_stall IN
    SELECT id FROM stalls WHERE market_id = v_market AND status = 'active'
    ORDER BY code_sort
  LOOP
    i := i + 1;
    v_cat := CASE WHEN i % 3 = 0 THEN v_cat_wear ELSE v_cat_food END;

    INSERT INTO stall_category_periods (market_id, stall_id, category_id, valid_from)
    SELECT v_market, v_stall, v_cat, v_today - 30
    WHERE NOT EXISTS (
      SELECT 1 FROM stall_category_periods WHERE stall_id = v_stall
    );

    -- ⛔ Har oltinchi rasta ATAYIN sotuvchisiz qoldiriladi: bozor
    --    hech qachon 100% to'la bo'lmaydi va panel «band, lekin
    --    to'lovsiz» holatini ko'rsata olishi kerak.
    CONTINUE WHEN i % 6 = 0;

    /* ⛔ `ORDER BY created_at` EMAS: 24 sotuvchi BIR tranzaksiyada
       yaratiladi va `now()` ularning hammasida BIR XIL — tartib
       aniqlanmagan bo'lib qolardi va `OFFSET` tasodifiy qator
       qaytarardi. Natijada bitta sotuvchiga 18 ta rasta biriktirilib,
       qolganlari bo'sh qolgan edi [ekranda ko'rildi]. Telefon raqami
       esa qat'iy va ketma-ket. */
    SELECT id INTO v_vendor FROM vendors
    WHERE market_id = v_market
    ORDER BY phone_e164
    OFFSET ((i - 1) % 24) LIMIT 1;

    INSERT INTO stall_assignments (market_id, stall_id, vendor_id, period)
    SELECT v_market, v_stall, v_vendor, daterange(v_today - 30, NULL)
    WHERE NOT EXISTS (
      SELECT 1 FROM stall_assignments
      WHERE stall_id = v_stall AND upper(period) IS NULL
    );
  END LOOP;

  -- ---------------------------------------------------------------------
  -- 4. Kunlik patta hisobi — oxirgi 7 kun.
  -- ---------------------------------------------------------------------
  FOR i IN 0..6 LOOP
    INSERT INTO daily_charges
      (market_id, stall_id, vendor_id, service_date, tariff_id,
       tariff_amount_soum, amount_soum)
    SELECT v_market, a.stall_id, a.vendor_id, v_today - i,
           CASE WHEN p.category_id = v_cat_wear THEN v_tar_wear ELSE v_tar_food END,
           CASE WHEN p.category_id = v_cat_wear THEN 10000 ELSE 8000 END,
           CASE WHEN p.category_id = v_cat_wear THEN 10000 ELSE 8000 END
    FROM stall_assignments a
    JOIN stall_category_periods p ON p.stall_id = a.stall_id
    WHERE a.market_id = v_market AND upper(a.period) IS NULL
    ON CONFLICT DO NOTHING;
  END LOOP;

  -- ---------------------------------------------------------------------
  -- 5. Smena va to'lovlar — hisoblanganning ~94% i.
  --
  -- ⛔ 100% ATAYIN EMAS: panelning bosh savoli «patta TO'LIQ
  --    yig'ilyaptimi?» va u to'liq bo'lmagan holatni ko'rsata olishi
  --    kerak. Aks holda ekranni faqat baxtli yo'lda ko'rgan bo'lardik.
  -- ---------------------------------------------------------------------
  /* ⛔ Kassirda OCHIQ smena bittadan ortiq bo'lolmaydi
     (`uq_cashier_shifts_market_id_cashier_open`) — bu to'g'ri qoida.
     Shuning uchun avvaldan ochiq qolgani yopiladi. */
  UPDATE cashier_shifts
  SET status = 'closed', closed_at = now(),
      system_soum = COALESCE(system_soum, 0),
      declared_soum = COALESCE(declared_soum, 0)
  WHERE market_id = v_market AND status = 'open';

  FOR i IN 0..6 LOOP
    /* ⛔ Avval OCHIQ smena: `ck_cashier_shifts_closed_has_declaration`
       yopiq smenani deklaratsiyasiz qabul qilmaydi va bu TO'G'RI —
       yopilgan smena hisobsiz bo'lmaydi. Shuning uchun tartib
       haqiqiy oqim bilan bir xil: ochiladi -> to'lov -> yopiladi. */
    INSERT INTO cashier_shifts
      (market_id, cashier_id, status, opened_at)
    VALUES (v_market, v_cashier, 'open',
            (v_today - i)::timestamptz + interval '6 hours')
    RETURNING id INTO v_shift;

    INSERT INTO payments
      (market_id, stall_id, vendor_id, service_date, amount_soum, quote_soum,
       kind, method, idempotency_key, request_fingerprint, shift_id, cashier_id,
       created_at)
    SELECT v_market, c.stall_id, c.vendor_id, c.service_date,
           c.amount_soum, c.amount_soum, 'payment', 'cash',
           'dev-seed-' || c.id::text, 'dev-seed', v_shift, v_cashier,
           (v_today - i)::timestamptz + interval '9 hours'
    FROM daily_charges c
    WHERE c.market_id = v_market
      AND c.service_date = v_today - i
      /* har 16-rasta to'lamagan -> qarz va «yig'ilmagan» paydo bo'ladi */
      AND (('x' || substr(md5(c.stall_id::text), 1, 8))::bit(32)::int % 16) <> 0
    ON CONFLICT DO NOTHING;

    SELECT COALESCE(SUM(amount_soum), 0) INTO v_paid
    FROM payments WHERE shift_id = v_shift;

    /* ⛔ Deklaratsiya farqi ATAYIN: kassir kartasi kamomadni ko'rsatishi
       kerak va u nol bo'lsa, o'sha shox hech qachon ekranda ko'rinmasdi. */
    UPDATE cashier_shifts
    SET status = 'closed',
        closed_at = (v_today - i)::timestamptz + interval '15 hours',
        system_soum = v_paid,
        /* ⛔ `GREATEST(0, …)`: deklaratsiya MANFIY bo'lolmaydi
           (`ck_cashier_shifts_declared_soum_non_negative`). To'lovsiz
           smenada 0 − 12 000 konstraytni buzardi. */
        declared_soum = GREATEST(
          0, v_paid - CASE WHEN i = 0 THEN 12000 ELSE 0 END
        )
    WHERE id = v_shift;
  END LOOP;

  RAISE NOTICE 'Namuna tayyor: bozor=%, sana=%', v_name, v_today;
END $$;

SELECT
  (SELECT count(*) FROM stalls)  AS rastalar,
  (SELECT count(*) FROM vendors) AS sotuvchilar,
  (SELECT count(*) FROM daily_charges WHERE service_date = (now() AT TIME ZONE 'Asia/Tashkent')::date) AS bugungi_hisob,
  (SELECT COALESCE(SUM(amount_soum),0) FROM daily_charges WHERE service_date = (now() AT TIME ZONE 'Asia/Tashkent')::date) AS hisoblangan,
  (SELECT COALESCE(SUM(amount_soum),0) FROM payments WHERE service_date = (now() AT TIME ZONE 'Asia/Tashkent')::date) AS yigilgan;
