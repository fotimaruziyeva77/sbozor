"use client";

import "client-only";

import {
  createContext,
  createElement,
  useContext,
  useMemo,
  useSyncExternalStore,
} from "react";

import type { ApiLocale, MarketSummary } from "@/lib/api-types";

/*
 * =============================================================================
 * ACCESS TOKEN FAQAT XOTIRADA SAQLANADI.
 *
 * Web Storage API (brauzerning doimiy va sessiya omborlari) bu faylda ham,
 * butun `src/` daraxtida ham ATAYIN ISHLATILMAYDI (T-01-60). Sabab: omborga
 * yozilgan token har qanday XSS uchun oddiy o'qish operatsiyasi bo'lib
 * qoladi — hujumchi uni chiqarib olib, 15 daqiqa emas, o'zi xohlagancha
 * ishlatadi. Qoida grep darvozasi bilan qulflangan, shuning uchun bu yerda
 * o'sha API nomlari literal sifatida yozilmaydi.
 *
 * Sahifa yangilanganda sessiya YO'QOLADI va u `POST /api/v1/auth/refresh`
 * orqali TIKLANADI: refresh token `httpOnly` cookie'da (`Path=/api/v1/auth`),
 * ya'ni JavaScript uni umuman ko'rmaydi. Bu "qayta login so'ralmasin"
 * talabini (D-03) token'ni omborga yozmasdan bajaradi.
 *
 * Holat modul darajasida saqlanadi (React tashqarisida), chunki `api-client`
 * ni React hook'iga bog'lab bo'lmaydi: u 401 javobda token yangilashi va
 * yangi tokenni shu yerga qaytarib yozishi kerak. React `useSyncExternalStore`
 * orqali shu manbaga OBUNA bo'ladi — ya'ni haqiqat manbai bitta.
 *
 * SSR eslatmasi: bu modul "use client" bo'lgani uchun server render paytida
 * ham yuklanadi, lekin unga YOZISH faqat brauzer hodisalaridan bo'ladi va
 * `serverSnapshot` har doim bo'sh sessiyani qaytaradi. Ya'ni bir
 * foydalanuvchining tokeni boshqa so'rovning render'iga tusha olmaydi.
 * `client-only` importi esa bu faylning Server Component grafiga tortilishini
 * butunlay bloklaydi.
 *
 * SERVER HOLATI KESHI HAM TENANT CHEGARASINING BIR QISMI (CR-01). Sessiya
 * IDENTIFIKATORI o'zgarganda (logout, yangi login, boshqa bozor) kesh
 * to'liq bo'shatilishi kerak, aks holda brauzer oldingi bozorning
 * zonalarini, rastalarini va sotuvchi F.I.Sh. + telefonini yangi kontekstda
 * chizib turadi. Bu modul so'rov keshi kutubxonasidan HECH NIMA IMPORT
 * QILMAYDI — yuqoridagi "React'dan mustaqil" sharti buzilardi va aynan shu
 * bog'lanmaganlik uning butun ishlash sharti. Aloqa `subscribeSessionReset`
 * obunachi reyestri orqali quriladi va uni `query-provider.tsx` ulaydi.
 * =============================================================================
 */

export type Principal = {
  /**
   * `null` bo'lishi mumkin: login javobida foydalanuvchi `id` si YO'Q
   * (unda faqat sessiya konteksti bor). Profil `GET /api/v1/me` bilan
   * keyinroq to'ldiriladi va bu to'ldirish yiqilsa ham login oqimi ishlaydi.
   */
  userId: string | null;
  phone: string | null;
  fullName: string | null;
  roles: readonly string[];
  marketId: string | null;
  marketName: string | null;
  isPlatformAdmin: boolean;
  locale: ApiLocale;
  mustChangePassword: boolean;
};

export type Session = {
  accessToken: string | null;
  principal: Principal | null;
  /** Login javobidan kelgan bozorlar (D-06 tanlash ekrani uchun). */
  markets: readonly MarketSummary[];
};

const EMPTY_SESSION: Session = {
  accessToken: null,
  principal: null,
  markets: [],
};

let memorySession: Session = EMPTY_SESSION;

const listeners = new Set<() => void>();

function emit(): void {
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/*
 * SESSIYA IDENTIFIKATORI kanali — yuqoridagi `listeners` dan ATAYIN ALOHIDA.
 *
 * NEGA IKKINCHI TO'PLAM: `listeners` — `useSyncExternalStore` ning render
 * obunasi va u sessiya HAR tegilganda ishlaydi (`setMarkets`,
 * `updatePrincipal`, har token yangilash). Keshni har `locale`
 * yangilanishida tozalash foydali hech narsa qilmasdi — faqat butun ekranni
 * qayta yuklaydigan foydasiz so'rov to'lqinini tug'dirardi.
 *
 * Bu kanal esa faqat BITTA hodisani olib yuradi: "kim/qaysi bozor
 * o'zgardi". Uni tinglovchi (`query-provider.tsx`) javoban keshni to'liq
 * bo'shatadi.
 */
const resetListeners = new Set<() => void>();

/**
 * Sessiya identifikatori o'zgarganda xabar beradi.
 *
 * Qaytgan funksiya obunani bekor qiladi (React `useEffect` tozalashi uchun).
 * HOOK EMAS va `AuthStore` tipiga ham qo'shilmaydi: uni ishlatadigan
 * `QueryProvider` `AuthProvider` dan YUQORIDA turadi, ya'ni kontekst orqali
 * yetib bora olmasdi.
 */
export function subscribeSessionReset(listener: () => void): () => void {
  resetListeners.add(listener);
  return () => {
    resetListeners.delete(listener);
  };
}

/*
 * `function` e'loni emas, `const`: shu shaklda chaqiruv shakli faylda
 * AYNAN uchta joyda — haqiqiy chaqiruvlarda — uchraydi, ta'rifning o'zida
 * emas. Ya'ni "kesh nechta joyda bo'shatiladi?" savoliga oddiy grep
 * to'g'ri javob beradi.
 */
const emitSessionReset = (): void => {
  for (const listener of resetListeners) listener();
};

/** Joriy sessiya — React'siz o'qish (`api-client` shu yo'ldan foydalanadi). */
export function readSession(): Session {
  return memorySession;
}

/**
 * Server snapshot HAR DOIM bir xil obyekt bo'lishi shart: yangi obyekt
 * qaytarilsa `useSyncExternalStore` cheksiz render tsikliga tushadi.
 */
function readServerSession(): Session {
  return EMPTY_SESSION;
}

/**
 * To'liq sessiyani almashtiradi (login yoki sessiya tiklashdan keyin).
 *
 * Kesh SHARTSIZ bo'shatiladi: yangi login — ta'rifi bo'yicha yangi
 * identifikator. Oldingi foydalanuvchining qatorlari yashab qolishi CR-01
 * ning ikkinchi yo'li edi ("logout -> boshqa foydalanuvchi bilan login",
 * bitta telefonda navbat bilan kirish MVP uchun real ssenariy).
 *
 * TARTIB MUHIM: avval kesh bo'shaydi, keyin `emit()` React'ni yangilaydi —
 * teskarisida React yangi identifikat bilan bir marta ESKI ma'lumot ustida
 * render qilib ulgurardi.
 */
export function setSession(next: Session): void {
  memorySession = next;
  emitSessionReset();
  emit();
}

/** Sessiyani o'chiradi (logout, refresh muvaffaqiyatsizligi). */
export function clearSession(): void {
  memorySession = EMPTY_SESSION;
  emitSessionReset();
  emit();
}

/**
 * Principal'ning bir qismini yangilaydi (masalan `locale` yoki
 * `mustChangePassword`). Principal yo'q bo'lsa jimgina e'tiborsiz qoldiriladi.
 */
export function updatePrincipal(patch: Partial<Principal>): void {
  const current = memorySession.principal;
  if (!current) return;
  memorySession = { ...memorySession, principal: { ...current, ...patch } };
  emit();
}

/** Bozorlar ro'yxatini yangilaydi (`GET /api/v1/markets` zaxira yo'li). */
export function setMarkets(markets: readonly MarketSummary[]): void {
  memorySession = { ...memorySession, markets };
  emit();
}

/**
 * Yangi access token + bozor konteksti (`/auth/refresh` va
 * `/auth/select-market` javoblari). Principal mavjud bo'lsa uning rollari va
 * bozori yangilanadi — eski rollar bilan menyu ko'rsatib qolmaslik uchun.
 *
 * ⚠ KESH TOZALASH BU YERDA SHARTLI, va shart qulaylik uchun emas: bu
 * funksiya `/auth/refresh` javobida ham chaqiriladi (`api-client.ts:164`)
 * va u yerda bozor O'ZGARMAYDI. Shartsiz tozalash har 15 daqiqalik token
 * yangilashda butun keshni yo'q qilib, foydalanuvchi ishlab turgan ekranni
 * sababsiz qayta yuklardi.
 *
 * Solishtirish `marketId` bo'yicha, `accessToken` bo'yicha EMAS: token har
 * yangilanishda o'zgaradi va u tenant identifikatori emas.
 */
export function applySession(next: {
  accessToken: string;
  roles: readonly string[];
  market: MarketSummary;
}): void {
  const current = memorySession.principal;
  // Yozuvdan OLDIN o'qiladi — keyin uni tiklab bo'lmasdi.
  const previousMarketId = current?.marketId ?? null;

  memorySession = {
    ...memorySession,
    accessToken: next.accessToken,
    principal: current
      ? {
          ...current,
          roles: next.roles,
          marketId: next.market.id,
          marketName: next.market.name,
        }
      : null,
  };

  if (previousMarketId !== next.market.id) emitSessionReset();
  emit();
}

export type AuthStore = Session & {
  setSession: typeof setSession;
  clearSession: typeof clearSession;
  updatePrincipal: typeof updatePrincipal;
  setMarkets: typeof setMarkets;
};

const AuthContext = createContext<AuthStore | null>(null);

/**
 * DIQQAT: bu fayl `.ts` (JSX emas), shuning uchun provayder `createElement`
 * bilan quriladi. Store'ning o'zi va uning provayderi bitta faylda turishi
 * ataylab: holatni o'zgartiradigan yagona yo'l shu modulda ko'rinib turadi.
 */
export function AuthProvider({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement {
  const session = useSyncExternalStore(
    subscribe,
    readSession,
    readServerSession,
  );

  const value = useMemo<AuthStore>(
    () => ({
      ...session,
      setSession,
      clearSession,
      updatePrincipal,
      setMarkets,
    }),
    [session],
  );

  return createElement(AuthContext.Provider, { value }, children);
}

export function useAuthStore(): AuthStore {
  const store = useContext(AuthContext);
  if (!store) {
    throw new Error("useAuthStore() faqat <AuthProvider> ichida ishlaydi");
  }
  return store;
}
