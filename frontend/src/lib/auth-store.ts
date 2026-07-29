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

/** To'liq sessiyani almashtiradi (login yoki sessiya tiklashdan keyin). */
export function setSession(next: Session): void {
  memorySession = next;
  emit();
}

/** Sessiyani o'chiradi (logout, refresh muvaffaqiyatsizligi). */
export function clearSession(): void {
  memorySession = EMPTY_SESSION;
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
 */
export function applySession(next: {
  accessToken: string;
  roles: readonly string[];
  market: MarketSummary;
}): void {
  const current = memorySession.principal;
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
