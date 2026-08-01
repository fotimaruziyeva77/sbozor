#!/usr/bin/env node
/**
 * "Yangi bozor" ustasiga YETIB BORISH yo'lining manba darvozasi (CR-03).
 *
 * NEGA KERAK: 2-faza usta serverini ham, ekranlarini ham to'liq qurdi va
 * 24 ta sabotaj testi bilan qulfladi — lekin mahsulotda unga BIRORTA yo'l
 * yo'q edi. 02-VERIFICATION.md buni 1-bo'shliq deb belgiladi, kod-ko'rik esa
 * "it is the feature not shipping" dedi.
 *
 * To'siq UCHTA va ular MUSTAQIL: marshrut ochilmasa yo'l yo'q; navigatsiya
 * yozuvi bo'lmasa yo'l topilmaydi; bo'sh ro'yxatda havola bo'lmasa toza
 * platformada unga yetib bo'lmaydi. Uchtasidan BIRI keyingi refaktoringda
 * jimgina qaytib kelsa, qolgan ikkitasi baribir yashil qolardi va butun
 * MARKET-01 yana bloklanardi (T-02-144).
 *
 * Vitest komponent testlari XULQNI o'lchaydi (`layout.test.tsx`,
 * `app-shell.test.tsx`, `market-picker.test.tsx`). Bu darvoza esa
 * MEXANIZMNI qulflaydi: masalan istisno `startsWith` ga aylantirilsa yoki
 * `permission` olib tashlansa, ba'zi xulq testlari hamon yashil qolishi
 * mumkin — bu yerdagi assertlar esa qaysi TO'SIQ qaytganini aniq aytadi.
 *
 * Nusxa emas, FAYLLARNING O'ZI o'qiladi (`role-gate.test.mjs` naqshi).
 *
 * ⚠ IZOH QATORLARI FILTRLANADI. Filtrsiz bu darvoza o'z-o'ziga qarshi
 * ishlardi: yuqoridagi uchala manba faylning docstringlari `/markets/new`
 * va `market_manage` ni MATN sifatida eslatadi, ya'ni oddiy `grep -c`
 * sanog'i kod o'chirilgan taqdirda ham izohdan to'lib, darvoza yashil
 * qolardi.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const FRONTEND_ROOT = path.join(import.meta.dirname, "..");
const SRC = path.join(FRONTEND_ROOT, "src");

const APP_LAYOUT = path.join(SRC, "app", "[locale]", "(app)", "layout.tsx");
const APP_SHELL = path.join(SRC, "components", "shell", "app-shell.tsx");
const MARKET_PICKER = path.join(SRC, "components", "auth", "market-picker.tsx");
const MESSAGES = path.join(FRONTEND_ROOT, "messages", "uz-Latn.json");

/** Ustaning boshlanish marshruti — uchala to'siq ham shu literalga tayanadi. */
const WIZARD_ROUTE = "/markets/new";

/**
 * Manba matni izoh qatorlarisiz.
 *
 * Satr BOSHIDAGI `//`, `/*` va `*` bilan boshlanuvchi qatorlar tashlanadi —
 * ya'ni bu loyihada ishlatiladigan blok-izoh uslubi (`/* ... ` + ` * ...`)
 * to'liq chiqib ketadi. Satr ICHIDAGI izohlar qoladi va bu ataylab: ular bu
 * kodbazada uchramaydi, murakkab tahlil esa darvozaning o'zini mo'rt
 * qilardi.
 */
function readCode(file) {
  return readFileSync(file, "utf8")
    .split(/\r?\n/u)
    .filter((line) => !/^\s*(\/\/|\/\*|\*)/u.test(line))
    .join("\n");
}

/* -------------------------------------------------------------------------- */
/* 1-TO'SIQ — marshrut istisnosi                                              */
/* -------------------------------------------------------------------------- */

test("1-to'siq: `(app)/layout.tsx` `/markets/new` ni marketId talabidan ozod qiladi", () => {
  const code = readCode(APP_LAYOUT);

  assert.ok(
    code.includes(WIZARD_ROUTE),
    `1-TO'SIQ QAYTDI: ${WIZARD_ROUTE} marshruti layout.tsx KODIDA yo'q (izohlar hisobga olinmaydi) — bozorsiz admin yana /select-market da qamalib qoladi`,
  );

  assert.ok(
    /usePathname/u.test(code),
    "1-TO'SIQ QAYTDI: `usePathname` ishlatilmayapti — istisno joriy marshrutga bog'lana olmaydi",
  );

  /*
   * Shart AYNAN `/select-market` redirectining oldidan olinadi.
   *
   * `principal.marketId === null` fayl bo'ylab IKKI marta uchraydi:
   * bu yerda va profil to'ldirish effektida (`if (principal.marketId ===
   * null || enrichStarted.current) return;`). Ikkinchisi TO'G'RI va u
   * bu rejada ATAYIN tegilmagan — bozorsiz profil so'ralmaydi. Shuning
   * uchun darvoza satrlarni emas, aynan REDIRECT bayonotini qo'riqlaydi.
   */
  const redirectIdx = code.indexOf('router.replace("/select-market")');
  assert.notEqual(
    redirectIdx,
    -1,
    "`/select-market` redirecti topilmadi — D-06 darvozasi butunlay o'chirilgan bo'lishi mumkin",
  );

  const conditionSlice = code.slice(Math.max(0, redirectIdx - 200), redirectIdx);

  /*
   * ENG MUHIM ASSERT: shart SO'ZSIZ bo'lmasligi kerak. Ilgari u aynan
   * `if (principal.marketId === null) {` edi va CR-03 shundan boshlangan.
   */
  const guarded =
    /if \(\s*([A-Za-z_$][\w$]*)\s*&&\s*principal\.marketId === null\s*\)\s*\{\s*$/u.exec(
      conditionSlice,
    );

  assert.ok(
    guarded,
    `1-TO'SIQ QAYTDI: so'zsiz redirect tiklandi — "...${conditionSlice.trim().split("\n").pop()}". Shart marshrut istisnosi bilan qo'riqlanishi SHART`,
  );

  const guardName = guarded[1];

  // Qo'riqchi MARSHRUTDAN hosil bo'ladi (rol yoki bayroqdan emas).
  const derivation = new RegExp(
    `const\\s+${guardName}\\s*=\\s*pathname\\s*!==\\s*([A-Za-z_$][\\w$]*)`,
    "u",
  ).exec(code);

  assert.ok(
    derivation,
    `1-TO'SIQ QAYTDI: \`${guardName}\` marshrutdan (\`pathname !== ...\`) hosil qilinmagan`,
  );

  const routeConst = derivation[1];
  const literal = new RegExp(
    `const\\s+${routeConst}\\s*=\\s*"([^"]+)"`,
    "u",
  ).exec(code);

  assert.ok(literal, `\`${routeConst}\` konstantasining qiymati topilmadi`);
  assert.equal(
    literal[1],
    WIZARD_ROUTE,
    `Istisno noto'g'ri marshrutga bog'langan: ${literal[1]}`,
  );

  /*
   * T-02-140: istisno PREFIKS emas, TENGLIK. `startsWith`/`includes` bo'lsa
   * `/markets/new-anything` ham bozorsiz ochilib, butun `(app)` daraxtiga
   * huquq oshirish yuzasi paydo bo'lardi.
   */
  assert.ok(
    !new RegExp(`(startsWith|includes|match)\\(\\s*${routeConst}`, "u").test(
      code,
    ),
    `T-02-140: istisno prefiks bo'yicha yozilgan (\`${routeConst}\` prefiks funksiyasiga berilgan) — u AYNAN bitta marshrutga TENGLIK bilan bog'lanishi SHART, aks holda /markets/new-anything ham bozorsiz ochilardi`,
  );

  /*
   * IKKINCHI JOY, va bu TAKROR EMAS: `ready` ham istisnodan foydalanmasa,
   * redirect yo'qoladi-yu, ekran ABADIY SKELET bo'lib qoladi.
   */
  assert.ok(
    new RegExp(`!${guardName}\\s*\\|\\|`, "u").test(code),
    `1-TO'SIQ YARIM QAYTDI: \`ready\` ifodasi \`${guardName}\` dan foydalanmayapti — redirect yo'q, lekin sahifa ham ochilmaydi (abadiy skelet)`,
  );
});

/* -------------------------------------------------------------------------- */
/* 2-TO'SIQ — navigatsiya yozuvi                                              */
/* -------------------------------------------------------------------------- */

test("2-to'siq: `app-shell.tsx` da `/markets/new` yozuvi `market_manage` bilan juftlangan", () => {
  const code = readCode(APP_SHELL);

  const arrayStart = code.indexOf("const NAV_ITEMS");
  assert.notEqual(arrayStart, -1, "`NAV_ITEMS` ro'yxati topilmadi");

  const arrayEnd = code.indexOf("\n];", arrayStart);
  assert.notEqual(arrayEnd, -1, "`NAV_ITEMS` ro'yxatining oxiri topilmadi");

  const navItems = code.slice(arrayStart, arrayEnd);

  // Yozuvlarda ichma-ich qavs yo'q, shuning uchun sodda ajratish yetadi.
  const entries = navItems.match(/\{[^{}]*\}/gu) ?? [];
  const wizardEntries = entries.filter((entry) =>
    entry.includes(`"${WIZARD_ROUTE}"`),
  );

  assert.equal(
    wizardEntries.length,
    1,
    `2-TO'SIQ QAYTDI: \`NAV_ITEMS\` da ${WIZARD_ROUTE} yozuvi ${wizardEntries.length} ta (kutilgan: 1) — usta menyudan yo'qoldi va URL qo'lda teriladi`,
  );

  const entry = wizardEntries[0];

  assert.ok(
    /permission:\s*"market_manage"/u.test(entry),
    `2-TO'SIQ QAYTDI: ${WIZARD_ROUTE} yozuvi \`market_manage\` bilan juftlanmagan — menyu huquqsiz rollarga ham shovqin ko'rsatadi`,
  );

  /*
   * UI-SPEC §12.3: yozuv `system` guruhida. Bu shunchaki tartib masalasi
   * emas — `market` guruhiga o'tkazilsa u mobil pastki panelning birinchi
   * to'rttasiga yaqinlashadi va "eng ko'pi 5 element" kontrakti buziladi.
   */
  assert.ok(
    /group:\s*"system"/u.test(entry),
    `UI-SPEC §12.3: ${WIZARD_ROUTE} yozuvi \`system\` guruhida bo'lishi SHART (mobil panel kontrakti)`,
  );

  // Yorliq kaliti HAQIQATAN mavjud — aks holda menyuda `MISSING_MESSAGE`.
  const labelKey = /labelKey:\s*"([^"]+)"/u.exec(entry);
  assert.ok(labelKey, "yozuvda `labelKey` yo'q");

  const messages = JSON.parse(readFileSync(MESSAGES, "utf8"));
  assert.ok(
    messages.nav[labelKey[1]],
    `\`nav.${labelKey[1]}\` tarjima kaliti \`uz-Latn.json\` da yo'q — menyuda xom kalit ko'rinardi`,
  );
});

/* -------------------------------------------------------------------------- */
/* 3-TO'SIQ — bo'sh ro'yxatdagi havola                                        */
/* -------------------------------------------------------------------------- */

test("3-to'siq: `market-picker.tsx` bo'sh ro'yxat tarmog'ida ustaga havola bor", () => {
  const code = readCode(MARKET_PICKER);

  const emptyBranch = code.indexOf("options.length === 0");
  assert.notEqual(
    emptyBranch,
    -1,
    "bo'sh ro'yxat tarmog'i (`options.length === 0`) topilmadi",
  );

  // Bo'sh tarmoq to'la ro'yxat renderidan (`<ul`) OLDIN tugaydi.
  const listRender = code.indexOf("<ul", emptyBranch);
  assert.notEqual(listRender, -1, "to'la ro'yxat renderi (`<ul`) topilmadi");

  const segment = code.slice(emptyBranch, listRender);

  const linkMatch = /<Link[\s\S]*?href=\{([A-Za-z_$][\w$]*)\}/u.exec(segment);
  assert.ok(
    linkMatch,
    "3-TO'SIQ QAYTDI: bo'sh ro'yxat tarmog'ida `<Link>` yo'q — toza platformada birinchi bozorni yaratib bo'lmaydi",
  );

  const routeConst = linkMatch[1];
  const literal = new RegExp(
    `const\\s+${routeConst}\\s*=\\s*"([^"]+)"`,
    "u",
  ).exec(code);

  assert.ok(literal, `\`${routeConst}\` konstantasining qiymati topilmadi`);
  assert.equal(
    literal[1],
    WIZARD_ROUTE,
    `Havola noto'g'ri marshrutga ketyapti: ${literal[1]}`,
  );

  /*
   * T-02-142: havola HUQUQ ostida. Huquqsiz odamga 403 ga olib boradigan
   * havola ko'rsatish UI-SPEC ning "bo'sh sarlavha yolg'on signal" qoidasi
   * bilan bir xil sinf.
   */
  const guard = /([A-Za-z_$][\w$]*)\s*\?\s*\(\s*<Link/u.exec(segment);
  assert.ok(
    guard,
    "T-02-142: havola shartsiz chizilyapti — u `market_manage` huquqi ostida bo'lishi SHART",
  );

  assert.ok(
    new RegExp(
      `const\\s+${guard[1]}\\s*=\\s*hasPermission\\([\\s\\S]*?"market_manage"`,
      "u",
    ).test(code),
    `T-02-142: \`${guard[1]}\` \`hasPermission(..., "market_manage")\` dan hosil qilinmagan`,
  );

  /*
   * "Chiqish" SAQLANADI: `canCreate` `false` bo'lgan foydalanuvchi uchun u
   * yagona chiqish yo'li. Bir boshi berk ko'chani ikkinchisiga almashtirish
   * tuzatish bo'lmasdi.
   */
  assert.ok(
    /nav\.logout/u.test(segment),
    "3-TO'SIQ YARIM QAYTDI: bo'sh holatdan «Chiqish» tugmasi olib tashlangan — huquqsiz foydalanuvchi qamalib qoladi",
  );
});
