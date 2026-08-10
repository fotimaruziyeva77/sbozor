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
  // O'QISH huquqlari YOZISHdan alohida (2-faza): direktor reestrni ko'radi,
  // lekin o'zgartira olmaydi (D-07). `vendor_view` esa `market_data_view`
  // dan ajratilgan, chunki sotuvchi — shaxsiy ma'lumot va uning O'QILISHI
  // ham auditda (D-09).
  "market_data_view",
  "vendor_view",
  "payment_create",
  // 6-faza (§5.6): kassirning O'QISH yuzasi va smena boshqaruvi.
  //
  // ⛔ NOMLAR SHU YERDA LITERAL SATR sifatida yoziladi va backenddan IMPORT
  // QILINMAYDI — `scripts/role-gate.test.mjs` ikkala faylni MATN sifatida
  // solishtiradi, ya'ni import darvozani o'zi tekshirayotgan qiymatga
  // bog'lab qo'yardi (05-15 darsi). Ikkinchi nusxa MAJBURIY.
  //
  // Sabablari (nega aynan bu ikkitasi va nega `market_data_view`/
  // `vendor_view`/`camera_view`/`report_view` kassirga BERILMAYDI) —
  // `services/core-api/app/security/rbac.py::Permission.BILLING_COLLECT_VIEW`
  // docstringida, bir joyda.
  "billing_collect_view",
  "shift_manage",
  "report_view",
  "occupancy_review",
  "dispute_decide",
  // Kamera yuzasi ham O'QISH/YOZISH ga ajratilgan (3-faza, D-15/D-07):
  // direktor `camera_view` oladi, `camera_manage` esa faqat platforma va
  // bozor adminida — NVR paroli va kashfiyot o'sha huquq ostida.
  "camera_view",
  "camera_manage",
] as const;
export type Permission = (typeof PERMISSIONS)[number];

const ROLE_PERMISSIONS: Readonly<Record<Role, readonly Permission[]>> = {
  // Platforma admini: bozorlararo yagona rol (D-06). `market_view_all` unga
  // RLS bypass BERMAYDI — u faqat bozor tanlash ekranini ochadi.
  //
  // `stall_manage`/`tariff_manage`/`vendor_manage` — MARKET-01 uchun
  // majburiy: usta rasta, tarif va sotuvchi qadamlarini o'z ichiga oladi.
  //
  // `camera_view`/`camera_manage` — CAM-08 uchun majburiy (3-faza): D-01
  // bo'yicha NVR'ni aynan platforma admini ulaydi. Faqat backendni
  // yangilash yetarli EMAS va faqat bu faylni yangilash undan ham yomon:
  // birinchisida tugma ko'rinmaydi (huquq bor), ikkinchisida tugma
  // ko'rinib turib 403 beradi. Shuning uchun ikkala matritsa BIRGA
  // o'zgaradi va `scripts/role-gate.test.mjs` ularni solishtiradi.
  platform_admin: [
    "market_view_all",
    "market_manage",
    "user_manage",
    "user_view",
    "audit_view",
    "stall_manage",
    "tariff_manage",
    "vendor_manage",
    "market_data_view",
    "vendor_view",
    "camera_view",
    "camera_manage",
  ],
  // D-07: FAQAT ko'rish + nizo qarori. `*_manage` huquqlarining YO'QLIGI —
  // bu qatorning asosiy mazmuni. 2-fazada qo'shilgan ikkita huquq ham
  // faqat o'qish.
  director: [
    "report_view",
    "audit_view",
    "camera_view",
    "dispute_decide",
    "user_view",
    "market_data_view",
    "vendor_view",
    // 6-faza: kutilayotgan patta BOZOR KESIMIDA (`/billing?day=bugun`).
    // `payment_create` va `shift_manage` BERILMADI — direktor o'qiydi.
    "billing_collect_view",
  ],
  market_admin: [
    "user_manage",
    "user_view",
    "audit_view",
    "stall_manage",
    "tariff_manage",
    "vendor_manage",
    "market_data_view",
    "vendor_view",
    "report_view",
    "camera_view",
    "camera_manage",
    "billing_collect_view",
    "shift_manage",
  ],
  // 6-fazagacha kassirda O'QISH huquqi UMUMAN YO'Q edi (o'lchandi: M-7) —
  // u to'lov yoza olardi, lekin nima yozayotganini ko'ra olmasdi.
  //
  // ⛔ `market_data_view` / `vendor_view` / `camera_view` / `report_view`
  // ATAYIN YO'Q: kassir yuzasida shaxsiy maydon strukturaviy ravishda
  // imkonsiz bo'lib qoladi (C-10). Sabablar `rbac.py` docstringida.
  cashier: ["payment_create", "billing_collect_view", "shift_manage"],
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

/** `roles.*` namespace'idagi kalitlar. */
export type RoleLabelKey =
  | "platformAdmin"
  | "director"
  | "marketAdmin"
  | "cashier"
  | "inspector";

/**
 * Rol nomining tarjima kaliti. Noma'lum rol — `null`, ya'ni xom
 * `market_admin` satri foydalanuvchiga HECH QACHON ko'rinmaydi.
 */
export function roleLabelKey(role: string): RoleLabelKey | null {
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
