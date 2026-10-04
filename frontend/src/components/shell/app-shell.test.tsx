/**
 * `app-shell.tsx` navigatsiya yozuvi — CR-03 ning IKKINCHI to'sig'i (02-18).
 *
 * NEGA AYNAN SHU FAYL: 02-VERIFICATION.md bo'yicha `NAV_ITEMS` da
 * `/markets/new` yozuvi HECH BIR rol uchun yo'q edi. Ya'ni marshrut ochilgan
 * taqdirda ham (`layout.test.tsx`) usta TOPILMAYDIGAN bo'lib qolardi va
 * foydalanuvchi URL'ni qo'lda terishi kerak edi — bu mahsulot emas.
 *
 * Test qulflaydigan xulq:
 *   1. `market_manage` huquqli rol menyuda «Yangi bozor» havolasini KO'RADI.
 *   2. NAZORAT: `market_manage` YO'Q rol (`market_admin`) uni KO'RMAYDI,
 *      lekin qolgan bo'limlarni ko'radi (ya'ni qobiq yiqilgani uchun emas).
 *   3. UI-SPEC §12.3: mobil pastki panelda ENG KO'PI 5 element (4 + «Ko'proq»)
 *      qoladi va yangi yozuv u yerga TUSHMAYDI — u `system` guruhida.
 *   4. UI-SPEC §12.3: yon panelda yozuv aynan «Tizim» guruhida turadi.
 *
 * DIQQAT: `permission` XAVFSIZLIK CHEGARASI EMAS (`app-shell.tsx:43-47`) —
 * u faqat menyuni yashiradi. 2-testning ma'nosi "ruxsat berilmadi" emas,
 * "shovqin ko'rsatilmadi". Haqiqiy darvoza `markets/new/page.tsx` da va
 * serverda (`POST /markets`, 02-11).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ComponentProps } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { AppShell } from "@/components/shell/app-shell";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import {
  markUnreachable,
  resetConnectivity,
} from "@/lib/connectivity";
import { ROLES } from "@/lib/rbac";

/*
 * `@/i18n/navigation` Next.js router kontekstiga tayanadi va u jsdom'da yo'q
 * (`wizard-stepper.test.tsx:40-49` bilan AYNI sabab). Mock `Link` ni oddiy
 * `<a>` ga aylantiradi; locale prefiksini qo'yish `next-intl` ning o'z
 * zimmasida va bu yerda sinalmaydi.
 */
const navigationMock = vi.hoisted(() => ({
  replace: vi.fn(),
  pathname: "/dashboard",
}));

vi.mock("@/i18n/navigation", () => ({
  // `prefetch` — Link'ning o'z propi, DOM atributi emas: `<a>` ga tushsa
  // React «non-boolean attribute» ogohlantirishini beradi.
  Link: ({
    children,
    href,
    prefetch: _prefetch,
    ...rest
  }: ComponentProps<"a"> & { prefetch?: boolean }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
  useRouter: () => ({ replace: navigationMock.replace }),
  usePathname: () => navigationMock.pathname,
}));

/** `nav.newMarket` — uz-Latn qiymati (test AYNAN shu katalogni yuklaydi). */
const NEW_MARKET_LABEL = "Yangi bozor";
const NEW_MARKET_HREF = "/markets/new";
/** `nav.groupSystem` — yon paneldagi «Tizim» sarlavhasi. */
const SYSTEM_GROUP_LABEL = "Tizim";
/** `nav.stalls` — 2-testdagi "qobiq baribir chizildi" nazorati. */
const STALLS_LABEL = "Rastalar";

/**
 * UI-SPEC §12.3 KONTRAKTI, `MOBILE_PRIMARY_COUNT` ning nusxasi EMAS.
 *
 * Ataylab modul konstantasidan import qilinmaydi: import qilinsa test
 * implementatsiyani o'ziga o'zi tasdiqlatardi (konstanta 8 ga o'zgarsa test
 * ham 8 ni kutib, jimgina yashil qolardi). Bu yerda 360px kenglikdagi
 * barmoq nishoni (WCAG 2.5.8) talab qiladigan SON qattiq yozilgan.
 */
const MOBILE_MAX_PRIMARY = 4;

function seedRoles(roles: readonly string[]): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998901234567",
      fullName: "Test Foydalanuvchi",
      roles,
      marketId: "11111111-1111-4111-8111-111111111111",
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: roles.includes("platform_admin"),
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
  });
}

function renderShell(): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  render(
    <NextIntlClientProvider locale="uz-Latn" messages={messages}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <AppShell>
            <p>sahifa-kontenti</p>
          </AppShell>
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );
}

/**
 * Mobil pastki panel.
 *
 * IKKALA `<nav>` ning ham `aria-label` i BIR XIL (`shell.sections`), shuning
 * uchun ular yorliq bilan ajratilmaydi. Ajratuvchi belgi — «Ko'proq»
 * TUGMASI: u faqat pastki panelda bor (yon panelda tugma umuman yo'q).
 * Indeks bo'yicha tanlash (`[1]`) markup tartibi o'zgarganda jimgina
 * noto'g'ri panelni tekshirib qo'yardi.
 */
function mobileBar(): HTMLElement {
  const bars = screen.getAllByRole("navigation");
  const bar = bars.find(
    (nav) => within(nav).queryAllByRole("button").length > 0,
  );
  expect(bar, "mobil pastki panel topilmadi").toBeDefined();
  return bar as HTMLElement;
}

beforeEach(() => {
  clearSession();
  vi.resetAllMocks();
  navigationMock.pathname = "/dashboard";
});

afterEach(() => {
  clearSession();
});

describe("AppShell — «Yangi bozor» navigatsiya yozuvi (CR-03)", () => {
  test("`market_manage` huquqli rol menyuda «Yangi bozor» havolasini ko'radi", () => {
    seedRoles(["platform_admin"]);
    renderShell();

    const link = screen.getByRole("link", { name: NEW_MARKET_LABEL });
    expect(link).toHaveAttribute("href", NEW_MARKET_HREF);
  });

  test("NAZORAT: `market_manage` YO'Q rolda havola KO'RINMAYDI", () => {
    // `market_admin` da `stall_manage`/`tariff_manage`/`vendor_manage` BOR,
    // lekin `market_manage` YO'Q (D-07) — bozor YARATISH platforma
    // adminining ishi.
    seedRoles(["market_admin"]);
    renderShell();

    expect(
      screen.queryByRole("link", { name: NEW_MARKET_LABEL }),
    ).not.toBeInTheDocument();

    /*
     * NAZORAT MAJBURIY: usiz bu test qobiq UMUMAN chizilmagan (masalan
     * render yiqilgan) holatda ham yashil ko'rinardi.
     */
    expect(
      screen.getAllByRole("link", { name: STALLS_LABEL }).length,
    ).toBeGreaterThan(0);
  });

  test("UI-SPEC §12.3: mobil panelda eng ko'pi 4 havola va yangi yozuv u yerda EMAS", () => {
    seedRoles(["platform_admin"]);
    renderShell();

    const bar = mobileBar();
    const directLinks = within(bar).getAllByRole("link");

    // 4 havola + «Ko'proq» tugmasi = 5 element (360px'da har biri ≥44px).
    expect(directLinks.length).toBeLessThanOrEqual(MOBILE_MAX_PRIMARY);
    expect(within(bar).getAllByRole("button")).toHaveLength(1);

    /*
     * Yangi yozuv `NAV_ITEMS` ning OXIRIDA va `system` guruhida — ya'ni u
     * «Ko'proq» varag'iga tushadi. Agar u ro'yxat boshiga ko'chirilsa,
     * pastki paneldan eng ko'p ishlatiladigan bo'lim siqib chiqarilardi.
     */
    expect(
      within(bar).queryByRole("link", { name: NEW_MARKET_LABEL }),
    ).not.toBeInTheDocument();
  });

  test("UI-SPEC §12.3: yon panelda yozuv «Tizim» guruhida turadi", () => {
    seedRoles(["platform_admin"]);
    renderShell();

    // Guruh sarlavhasi va uning havolalari bitta konteynerda (`app-shell.tsx`
    // dagi `NAV_GROUPS` render tarmog'i).
    const groupHeading = screen.getByText(SYSTEM_GROUP_LABEL);
    const group = groupHeading.parentElement;
    expect(group, "«Tizim» guruhi konteyneri topilmadi").not.toBeNull();

    expect(
      within(group as HTMLElement).getByRole("link", {
        name: NEW_MARKET_LABEL,
      }),
    ).toHaveAttribute("href", NEW_MARKET_HREF);
  });
});

/* ---------------------------------------------------------------------------
 * 5-FAZA — NAZORATCHINING UYI (W0-F1, W0-F5, 05-UI-SPEC §4.6).
 *
 * ⛔ NEGA BU TEST ENG MUHIMI. Bugungacha `inspector` roli navigatsiyada
 * FAQAT Boshqaruv panelini ko'rardi — ya'ni nazoratchining ishi uchun
 * ekran UMUMAN YO'Q edi. `/review` uning BIRINCHI ekrani; agar u
 * `NAV_ITEMS` ga tushmasa, marshrut ochilgan taqdirda ham u
 * TOPILMAYDIGAN bo'lib qolardi va nazoratchi URL'ni qo'lda terishi
 * kerak bo'lardi. Bu 02-18 dagi `/markets/new` to'sig'ining aynan
 * takrori va shuning uchun darvoza ham o'sha joyda.
 *
 * ⛔ W0-F5 — RBAC O'ZGARMAYDI, LEKIN TASDIQLANADI. `occupancy_review`
 * va `report_view` IKKALA matritsada ham ALLAQACHON bor (M-8), ya'ni bu
 * fazada `lib/rbac.ts` ham, `app/security/rbac.py` ham TEGILMAYDI. Bu
 * bloknig vazifasi — keyingi ijrochi yangi `Permission` O'YLAB
 * TOPMASLIGI: matritsani bir tomonlama o'zgartirish tugmani ko'rsatib
 * turib 403 beradigan holat tug'dirardi (`rbac.ts:62-67`).
 *
 * ⚠ O-03 (05-UI-SPEC §16.4): `platform_admin` da `report_view` YO'Q, ya'ni
 * u "Bandlik" ni KO'RMAYDI. Bu ataylab qabul qilingan: rollar TO'PLAM
 * (1-faza D-05) va tekshirish uchun platforma adminiga `market_admin`
 * roli ham beriladi. Shuning uchun quyida "Bandlik" ni `director`
 * bo'yicha sinaymiz — unda `report_view` bor va u hisobotning ASOSIY
 * iste'molchisi.
 * ------------------------------------------------------------------------ */

/** `nav.review` / `nav.occupancy` — uz-Latn qiymatlari. */
const REVIEW_LABEL = "Ko'rib chiqish";
const REVIEW_HREF = "/review";
const OCCUPANCY_LABEL = "Bandlik";
const OCCUPANCY_HREF = "/occupancy";
/** `nav.dashboard` — "qobiq baribir chizildi" nazorati. */
const DASHBOARD_LABEL = "Boshqaruv paneli";

/**
 * 05-UI-SPEC §12.3 KONTRAKTI: mobil pastki panelda eng ko'pi 5 element.
 *
 * `MOBILE_PRIMARY_COUNT + 1` sifatida HISOBLANMAYDI — yuqoridagi
 * `MOBILE_MAX_PRIMARY` bilan aynan bir xil sabab: import qilingan
 * konstanta testni implementatsiyaga o'ziga o'zi tasdiqlatardi.
 */
const MOBILE_MAX_ELEMENTS = 5;

/**
 * Mobil pastki panel — SINF bo'yicha, tugma bo'yicha EMAS.
 *
 * ⚠ Yuqoridagi `mobileBar()` "Ko'proq" TUGMASINI ajratuvchi belgi sifatida
 *   ishlatadi va u HAR ROL uchun ishlamaydi: `inspector` da jami ikki
 *   yozuv bor, ya'ni overflow BO'SH va tugma umuman chizilmaydi.
 *   Sinf bo'yicha tanlash ikkala holatda ham ishlaydi, chunki `md:hidden`
 *   faqat pastki panelda bor (yon panel — `hidden … md:flex`).
 */
function mobileBarByBreakpoint(): HTMLElement {
  const bars = screen
    .getAllByRole("navigation")
    .filter((nav) => nav.className.includes("md:hidden"));
  expect(bars, "mobil pastki panel AYNAN bitta bo'lishi kerak").toHaveLength(1);
  return bars[0];
}

describe("AppShell — nazoratchining uyi va bandlik hisoboti (05-UI-SPEC §4.6)", () => {
  test("`inspector` navigatsiyada «Ko'rib chiqish» ni KO'RADI", () => {
    seedRoles(["inspector"]);
    renderShell();

    // Havola yon panelda ham, pastki panelda ham chiziladi — shuning uchun
    // `getAllBy…`; muhimi UMUMAN mavjudligi va `href` ning to'g'riligi.
    const links = screen.getAllByRole("link", { name: REVIEW_LABEL });
    expect(links.length).toBeGreaterThan(0);
    for (const link of links) {
      expect(link).toHaveAttribute("href", REVIEW_HREF);
    }
  });

  /*
   * ⛔⛔ DA'VO TESKARISIGA O'ZGARDI — VA BU ONGLI QAROR (260820).
   *
   *   Ilgari bu test «`inspector` da Bandlik KO'RINMAYDI» deb turardi,
   *   chunki menyu yozuvi `report_view` bilan darvozalangan edi.
   *
   *   Jonli UAT'da ma'lum bo'ldiki, bu buzuq halqa: bandlikni AYNAN
   *   nazoratchi o'lchaydi — kun bo'yi kadr ko'rib qaror yozadi —
   *   lekin o'z ishining NATIJASINI ko'ra olmaydi. Sahifaning
   *   O'ZIDA unga atalgan shox (`canReview`) allaqachon bor edi,
   *   ya'ni ekran nazoratchini kutardi, eshik esa yopiq edi.
   *
   *   ⚠ SIZIB CHIQISH YO'Q: bu yuzada PUL maydoni umuman yo'q —
   *     javob `stalls/occupied/empty/no_coverage/human_confirmed`
   *     sanoqlaridan iborat.
   *
   *   Menyu yozuvi endi IKKI huquqni «birortasi yetsa» qoidasi bilan
   *   qabul qiladi: nazoratchi ham, direktor ham ko'radi.
   */
  test("`inspector` navigatsiyada «Bandlik» ni KO'RADI (`occupancy_review`)", () => {
    seedRoles(["inspector"]);
    renderShell();

    const links = screen.getAllByRole("link", { name: OCCUPANCY_LABEL });
    expect(links.length).toBeGreaterThan(0);

    /*
     * NAZORAT MAJBURIY: usiz bu test qobiq UMUMAN chizilmagan holatda ham
     * yashil ko'rinardi (`market_manage` testidagi bilan bir xil sabab).
     */
    expect(
      screen.getAllByRole("link", { name: DASHBOARD_LABEL }).length,
    ).toBeGreaterThan(0);
  });

  test("NAZORAT: `cashier` da «Bandlik» KO'RINMAYDI — ikkala huquq ham yo'q", () => {
    seedRoles(["cashier"]);
    renderShell();

    expect(
      screen.queryByRole("link", { name: OCCUPANCY_LABEL }),
    ).not.toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { name: DASHBOARD_LABEL }).length,
    ).toBeGreaterThan(0);
  });

  test("`director` navigatsiyada «Bandlik» ni ko'radi (`report_view`)", () => {
    seedRoles(["director"]);
    renderShell();

    const links = screen.getAllByRole("link", { name: OCCUPANCY_LABEL });
    expect(links.length).toBeGreaterThan(0);
    for (const link of links) {
      expect(link).toHaveAttribute("href", OCCUPANCY_HREF);
    }

    // NAZORAT: direktorda `occupancy_review` YO'Q — ko'rib chiqish
    // nazoratchining ishi, direktor esa NATIJANI o'qiydi.
    expect(
      screen.queryByRole("link", { name: REVIEW_LABEL }),
    ).not.toBeInTheDocument();
  });

  test("⛔ `/review/blind` navigatsiyada YO'Q — u sessiya, bo'lim emas (§7.2)", () => {
    seedRoles(["inspector"]);
    renderShell();

    /*
     * Menyudagi havola ko'r auditni "yana bir ro'yxat" qilib ko'rsatardi.
     * Unga faqat `/review` uyidan, OCHIQ NIYAT bilan kiriladi — aks holda
     * nazoratchi u yerga tasodifan tushib, o'zgartirib bo'lmaydigan javob
     * berib qo'yardi (D-17, 4-himoya).
     *
     * Tekshiruv RENDER natijasida, manba faylida `grep` bilan emas: izohda
     * yozilgan yo'l `grep` ni qizartirardi, holbuki u navigatsiyada emas.
     */
    const blind = screen
      .getAllByRole("link")
      .filter((link) => link.getAttribute("href")?.startsWith("/review/"));
    expect(blind).toHaveLength(0);
  });

  test("HAR ROLDA mobil panelda eng ko'pi 5 element (§12.3, M-7)", () => {
    /*
     * ROLLAR RO'YXATI `rbac.ts` DAN OLINADI, bu yerda qo'lda
     * yozilmaydi (§S-10): yangi rol qo'shilganda test uni AVTOMATIK
     * qamraydi. Qo'lda yozilgan ro'yxat aynan yangi rolda jimgina
     * bo'shab qolardi.
     */
    expect(ROLES.length).toBeGreaterThanOrEqual(5);

    for (const role of ROLES) {
      cleanup();
      clearSession();
      seedRoles([role]);
      renderShell();

      const bar = mobileBarByBreakpoint();
      const elements =
        within(bar).queryAllByRole("link").length +
        within(bar).queryAllByRole("button").length;

      expect(
        elements,
        `«${role}» rolida pastki panelda ${elements} element bor — 360px da ` +
          "har biri 44px dan pastga tushardi (WCAG 2.5.8)",
      ).toBeLessThanOrEqual(MOBILE_MAX_ELEMENTS);

      // NAZORAT: panel BO'SH bo'lsa yuqoridagi assert jimgina o'tardi.
      expect(elements, `«${role}» rolida pastki panel bo'sh`).toBeGreaterThan(0);
    }
  });
});

/*
 * ===========================================================================
 * YON PANELDA GURUH UYUMI BO'LMAYDI (261004, o'lchangan).
 *
 * O'lchov: direktor va bozor adminida 14 banddan 11 TASI bitta «Bozor»
 * sarlavhasi ostida edi. Guruhlash bor edi, lekin hech narsani ajratmasdi —
 * ko'z har safar ro'yxatni boshidan o'qishga majbur edi.
 *
 * Bu darvoza yangi band qo'shilganda uyum QAYTIB o'smasligini qulflaydi:
 * `NAV_ITEMS` ga yozuv qo'shgan odam uni to'g'ri guruhga qo'yishi SHART,
 * aks holda shu test qizaradi va sabab ekranda yoziladi.
 * ===========================================================================
 */
describe("AppShell — yon panelda guruh uyumi bo'lmaydi (261004)", () => {
  /**
   * Bitta sarlavha ostidagi eng ko'p band.
   *
   * ⚠ ANIQ SONGA QADALMAGAN: 6 — «ko'z bir qarashda qamrab oladi» chegarasi,
   *   bugungi eng kattasi esa 5 (direktorning «Bozor» i). Ya'ni bitta band
   *   qo'shish uchun joy bor, ikkitasi esa qaror talab qiladi.
   */
  const MAX_GURUH = 6;

  const GURUHLAR = [
    messages.nav.groupMarket,
    messages.nav.groupWatch,
    messages.nav.groupMoney,
    messages.nav.groupSystem,
  ] as const;

  /** Yon panel: «Ko'proq» TUGMASI faqat pastki panelda — `mobileBar()` bilan ayni mantiq. */
  function sidebar(): HTMLElement {
    const bars = screen.getAllByRole("navigation");
    const bar = bars.find(
      (nav) => within(nav).queryAllByRole("button").length === 0,
    );
    expect(bar, "yon panel topilmadi").toBeDefined();
    return bar as HTMLElement;
  }

  /** Sarlavha -> o'sha guruhdagi havolalar soni. Guruh chizilmasa — yozuv yo'q. */
  function guruhSanogi(): Map<string, number> {
    const panel = sidebar();
    const natija = new Map<string, number>();
    for (const sarlavha of GURUHLAR) {
      const topildi = within(panel).queryByText(sarlavha);
      if (topildi === null) continue;
      const konteyner = topildi.parentElement;
      expect(konteyner, `«${sarlavha}» guruhi konteyneri yo'q`).not.toBeNull();
      natija.set(
        sarlavha,
        within(konteyner as HTMLElement).getAllByRole("link").length,
      );
    }
    return natija;
  }

  test.each([
    ["director"],
    ["market_admin"],
    ["platform_admin"],
    ["cashier"],
    ["inspector"],
  ])("`%s`: hech bir guruh chegaradan oshmaydi", (rol) => {
    seedRoles([rol]);
    renderShell();

    const oshganlar = [...guruhSanogi()]
      .filter(([, n]) => n > MAX_GURUH)
      .map(([g, n]) => `${g}=${n}`);

    expect(
      oshganlar,
      `${rol} da guruh ${MAX_GURUH} banddan oshdi: ${oshganlar.join(", ")}`,
    ).toEqual([]);
  });

  /*
   * ⛔⛔ QUYI CHEGARA — USIZ YUQORIDAGI DARVOZA TRIVIAL O'TARDI.
   *
   * Chizish buzilsa yoki sarlavhalar topilmasa, `guruhSanogi()` BO'SH
   * qaytarardi va «oshgan guruh yo'q» asserti yashil bo'lardi. Aynan
   * `MINIMUM_SCANNED_ROUTES` qo'riqlaydigan nosozlik sinfi.
   */
  test("QUYI CHEGARA: direktor haqiqatan to'rt guruhni va 14 havolani ko'radi", () => {
    seedRoles(["director"]);
    renderShell();

    const sanoq = guruhSanogi();

    // «Tizim» dan tashqari uchta guruh ham chizilgan bo'lishi SHART —
    // ya'ni bo'linish haqiqatan ishlayapti, hammasi bir uyumda emas.
    expect([...sanoq.keys()].sort()).toEqual(
      [...GURUHLAR].sort((a, b) => a.localeCompare(b)),
    );

    // Jami havola soni: 14 band, biri («Boshqaruv paneli») guruhsiz.
    const jami = [...sanoq.values()].reduce((a, b) => a + b, 0);
    expect(jami, "direktorda guruhli havolalar soni kutilganidan kam").toBe(13);

    // Va eng kattasi AYNAN 5 — o'lchangan holat kodda qotib qolsin.
    expect(Math.max(...sanoq.values())).toBe(5);
  });
});

/*
 * ===========================================================================
 * ALOQA YO'Q BANNERI — HAR EKRANDA (261004).
 *
 * Ilgari uzilish faqat HARAKAT paytida ko'rinardi: kassir «To'lash» ni
 * bosardi va xato olardi. Navbatda sotuvchi turganda bu har biriga bitta
 * behuda urinish degani. Banner qobiqda, ya'ni rolga bog'liq emas:
 * direktor panelidagi «bugungi daromad» ham uzilishda jimgina kechagi
 * holatni ko'rsatib turardi.
 * ===========================================================================
 */
describe("AppShell — aloqa yo'q banneri (261004)", () => {
  const BANNER = messages.shell.offlineBanner;

  afterEach(() => {
    resetConnectivity();
  });

  test("aloqa BOR bo'lsa banner CHIZILMAYDI", () => {
    seedRoles(["cashier"]);
    renderShell();

    expect(screen.queryByText(BANNER)).toBeNull();
  });

  test("aloqa YO'Q bo'lsa banner chiziladi va e'lon qilinadi", () => {
    markUnreachable();
    seedRoles(["cashier"]);
    renderShell();

    const banner = screen.getByText(BANNER);
    expect(banner).toBeInTheDocument();
    /*
     * ⚠ `role="status"` + `aria-live` MAJBURIY: banner sahifa ALLAQACHON
     *   ochiq bo'lganda paydo bo'ladi, ya'ni ekran o'quvchisi uni o'zi
     *   sezmaydi — e'lon qilinishi kerak.
     */
    expect(banner).toHaveAttribute("role", "status");
    expect(banner).toHaveAttribute("aria-live", "polite");
  });

  test("banner ROLGA bog'liq emas — direktorda ham chiziladi", () => {
    markUnreachable();
    seedRoles(["director"]);
    renderShell();

    expect(screen.getByText(BANNER)).toBeInTheDocument();
  });
});
