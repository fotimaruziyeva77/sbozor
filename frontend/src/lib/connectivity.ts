/**
 * SERVERGA YETIB BORILDIMI — bitta boolean, bitta haqiqat manbai.
 *
 * =============================================================================
 * ⛔⛔ `navigator.onLine` ATAYIN ISHLATILMAYDI VA BU ENG MUHIM QAROR.
 *
 * Bozor kompyuteri NVR bilan BITTA LAN da turadi. Modem internetni yo'qotsa
 * ham tarmoq interfeysi tirik qoladi va brauzer `navigator.onLine === true`
 * deb javob beradi. Ya'ni u aynan kerak bo'lgan paytda — bozorda internet
 * uzilgan kuni — YOLG'ON «ulangan» deydi.
 *
 * Shuning uchun signal HAQIQIY so'rov natijasidan olinadi: `fetch` ning o'zi
 * yiqilsa — yetib borilmadi; javob KELSA (hatto 500 bo'lsa ham) — server
 * tirik, demak aloqa bor. HTTP xatosi aloqa muammosi EMAS.
 * =============================================================================
 *
 * ⚠ BEKOR QILINGAN SO'ROV HISOBGA OLINMAYDI (`isAbortError`). `AbortError`
 *   ham `fetch` ning `catch` iga tushadi, lekin u foydalanuvchi sahifadan
 *   chiqib ketgani yoki `react-query` so'rovni to'xtatgani degani. Uni
 *   «aloqa yo'q» deb hisoblasak, tez navigatsiyada banner YOLG'ON chiqardi.
 */
import { useSyncExternalStore } from "react";

let unreachable = false;

/*
 * `auth-store.ts:103` bilan AYNI naqsh: `useSyncExternalStore` ning render
 * tarmog'i uchun alohida to'plam. Snapshot — PRIMITIV `boolean`, ya'ni har
 * o'qishda yangi havola qaytmaydi va cheksiz render tsikli bo'lmaydi
 * (`auth-store.ts:163` dagi tuzoq).
 */
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

/**
 * `fetch` yiqildi — serverga yetib borilmadi.
 *
 * ⚠ Faqat `api-client.ts` dagi YAGONA `catch` dan chaqiriladi. Boshqa
 *   joydan chaqirilsa holat ikki manbadan boshqarilib, qaysi biri rost
 *   ekani aniqlanmay qolardi.
 */
export function markUnreachable(): void {
  if (unreachable) return;
  unreachable = true;
  emit();
}

/** Javob keldi (status MUHIM EMAS) — server tirik. */
export function markReachable(): void {
  if (!unreachable) return;
  unreachable = false;
  emit();
}

/**
 * `AbortError` mi — ya'ni so'rovni BIZ to'xtatdikmi.
 *
 * `DOMException` nomi bo'yicha aniqlanadi: `instanceof DOMException` jsdom
 * va Node orasida bir xil ishlamaydi, nom esa ikkalasida ham `AbortError`.
 */
export function isAbortError(cause: unknown): boolean {
  return (
    typeof cause === "object" &&
    cause !== null &&
    "name" in cause &&
    (cause as { name?: unknown }).name === "AbortError"
  );
}

/** Testlar uchun: holatni boshlang'ich qiymatga qaytaradi. */
export function resetConnectivity(): void {
  unreachable = false;
  listeners.clear();
}

/** Hozir serverga yetib borilmayaptimi — React'dan TASHQARIDA o'qish uchun. */
export function isUnreachable(): boolean {
  return unreachable;
}

function snapshot(): boolean {
  return unreachable;
}

/*
 * ⛔ SERVER SNAPSHOT'I `false` — ya'ni SSR da banner CHIZILMAYDI.
 *   Server tomonda so'rov tarixi yo'q, demak «aloqa yo'q» degan da'vo
 *   asossiz bo'lardi va sahifa har safar banner bilan ochilib, keyin uni
 *   olib tashlab, ko'zga urilardi (hydration sakrashi).
 */
function serverSnapshot(): boolean {
  return false;
}

/** Serverga yetib borilmayaptimi — React komponentlari uchun. */
export function useUnreachable(): boolean {
  return useSyncExternalStore(subscribe, snapshot, serverSnapshot);
}
