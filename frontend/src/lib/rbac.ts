/*
 * =============================================================================
 * BU FAYL FAQAT UI UCHUN.
 *
 * Bu yerdagi tekshiruv HECH QACHON xavfsizlik chegarasi emas (T-01-62). U
 * faqat "ko'rinmasin" degan savolga javob beradi: menyu bandi, tugma,
 * bo'lim. Har qanday HAQIQIY qaror serverda `require_permission(...)`
 * dependency'si bilan qabul qilinadi (01-06) va yashirilgan tugmaning
 * so'rovini qo'lda yuborgan foydalanuvchi baribir 403 oladi.
 *
 * Ya'ni: bu matritsani buzish UI'ni chalkashtiradi, ma'lumotni ochmaydi.
 *
 * Manba: `services/core-api/app/security/rbac.py` (D-07). Ikkisi qo'lda
 * sinxron saqlanadi — matritsa MVP'da ataylab kodda va uni o'zgartirish
 * ikkala tomonda ham kod review'dan o'tadi.
 * =============================================================================
 */

export const ROLES = [
  "platform_admin",
  "director",
  "market_admin",
  "cashier",
  "inspector",
] as const;
export type Role = (typeof ROLES)[number];

export const PERMISSIONS = [
  "user_manage",
  "user_view",
  "audit_view",
  "market_view_all",
  "market_manage",
  "stall_manage",
  "tariff_manage",
  "vendor_manage",
  "payment_create",
  "report_view",
  "occupancy_review",
  "dispute_decide",
  "camera_view",
] as const;
export type Permission = (typeof PERMISSIONS)[number];

const ROLE_PERMISSIONS: Readonly<Record<Role, readonly Permission[]>> = {
  // Platforma admini: bozorlararo yagona rol (D-06). `market_view_all` unga
  // RLS bypass BERMAYDI — u faqat bozor tanlash ekranini ochadi.
  platform_admin: [
    "market_view_all",
    "market_manage",
    "user_manage",
    "user_view",
    "audit_view",
  ],
  // D-07: FAQAT ko'rish + nizo qarori. `*_manage` huquqlarining YO'QLIGI —
  // bu qatorning asosiy mazmuni.
  director: [
    "report_view",
    "audit_view",
    "camera_view",
    "dispute_decide",
    "user_view",
  ],
  market_admin: [
    "user_manage",
    "user_view",
    "audit_view",
    "stall_manage",
    "tariff_manage",
    "vendor_manage",
    "report_view",
    "camera_view",
  ],
  cashier: ["payment_create"],
  inspector: ["occupancy_review"],
};

/**
 * Rollar TO'PLAMINING huquqlar birlashmasi (D-05): kichik bozorda bir odam
 * ham bozor admini, ham kassir bo'ladi.
 *
 * Noma'lum rol nomi JIMGINA e'tiborsiz qoldiriladi — access token 15 daqiqa
 * yashaydi, ya'ni rol o'chirilgandan keyin ham eski token bir muddat kelib
 * turadi. To'g'ri xulq — o'sha roldan huquq bermaslik, UI'ni yiqitish emas.
 */
export function hasPermission(
  roles: readonly string[],
  permission: Permission,
): boolean {
  return roles.some((role) =>
    (ROLE_PERMISSIONS[role as Role] ?? []).includes(permission),
  );
}

/** Rol nomining tarjima kaliti (`roles.*`). Noma'lum rol — `null`. */
export function roleLabelKey(role: string): string | null {
  switch (role) {
    case "platform_admin":
      return "platformAdmin";
    case "director":
      return "director";
    case "market_admin":
      return "marketAdmin";
    case "cashier":
      return "cashier";
    case "inspector":
      return "inspector";
    default:
      return null;
  }
}
