"use client";

import { useId, useMemo, useState } from "react";
import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import type { MapZone } from "@/lib/api-types";

/*
 * =============================================================================
 * DL-1 — ZONA MA'LUMOTLARI: RASTA BIRIKTIRISH VA VERSIYA.
 *
 * -----------------------------------------------------------------------
 * ⛔ «TIKLASH» TUGMASI QURILMAYDI — VA BU MAHSULOT QARORI
 * -----------------------------------------------------------------------
 * Tahrir har safar YANGI `version` yaratadi, eskisi `is_active=false`
 * bo'ladi (D-07). Eski versiyani «tiklash» amali YANGI versiya yaratardi,
 * ya'ni tarixda «3-versiya aslida 1-versiyaning nusxasi» degan ikki
 * ma'noli qator paydo bo'lardi va «bu rasta qaysi kontur bo'yicha
 * o'lchangan?» savoli javobsiz qolardi. Kerak bo'lsa — qaytadan
 * chiziladi (§6.6, §16.2).
 *
 * ⚠ DIALOG MATNIDA BU HAQDA HECH NIMA YOZILMAYDI. Sabab rejada va
 *   SUMMARY da qoladi: yo'q imkoniyat haqida gapirish uni «bor edi,
 *   olib tashlandi» qilib ko'rsatardi va foydalanuvchini izlashga
 *   majburlardi.
 *
 * -----------------------------------------------------------------------
 * ⚠ «OLDINGI VERSIYALAR» RO'YXATI HAM QURILMADI — MA'LUMOT MANBAI YO'Q
 * -----------------------------------------------------------------------
 * §6.6 `<details>` ichida «sana + kim» ro'yxatini ko'rsatadi. Server esa
 * FAQAT faol zonalarni qaytaradi (`GET /camera-zones`, 05-06): eskirgan
 * qatorlar jadvalda qoladi, lekin ular uchun marshrut YO'Q. Bo'sh
 * `<details>` qo'yish «tarix yo'q» degan YOLG'ON xabar berardi, shuning
 * uchun bu yerda faqat JORIY versiya raqami ko'rsatiladi va yetishmayotgan
 * marshrut SUMMARY da ochiq band sifatida qayd etiladi.
 *
 * -----------------------------------------------------------------------
 * ⛔ RASTA RO'YXATI `GET /stalls/map` DAN, `GET /stalls` DAN EMAS
 * -----------------------------------------------------------------------
 * Reestr KURSOR bilan sahifalanadi, ya'ni «qatordagi rastalar» uchun
 * bir necha so'rov kerak bo'lardi va tartib sahifalar chegarasida
 * uzilardi. Xarita esa BARCHA rastani `code_sort` tartibida, bitta
 * so'rovda beradi va uning kesh yozuvi DL-2 bilan BIR XIL — ya'ni
 * ikkinchi so'rov umuman ketmaydi.
 * =============================================================================
 */

/** Qidiruv natijalarining chegarasi — ro'yxat dialogni bosib ketmasin. */
const MAX_MATCHES = 12;

export function ZoneDetailDialog({
  onAssignStall,
  onDelete,
  onOpenChange,
  open,
  stallCode,
  stallId,
  version,
  zones,
}: {
  onAssignStall: (stall: { code: string; id: string }) => void;
  onDelete: () => void;
  onOpenChange: (open: boolean) => void;
  open: boolean;
  stallCode: string | null;
  stallId: string | null;
  /** `null` — hali saqlanmagan zona, ya'ni versiyasi ham yo'q. */
  version: number | null;
  zones: readonly MapZone[];
}) {
  const t = useTranslations();
  const searchId = useId();
  const [query, setQuery] = useState("");

  const matches = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase("uz-Latn");
    const all = zones.flatMap((zone) =>
      zone.cells.map((cell) => ({
        code: cell.code,
        id: cell.id,
        zoneName: zone.name,
      })),
    );
    const filtered =
      needle === ""
        ? all
        : all.filter((cell) =>
            cell.code.toLocaleLowerCase("uz-Latn").includes(needle),
          );
    return filtered.slice(0, MAX_MATCHES);
  }, [query, zones]);

  return (
    <Dialog.Root onOpenChange={onOpenChange} open={open}>
      <Dialog.Content
        description={t("cameraZones.assignStall")}
        size="sm"
        srOnlyDescription
        title={t("cameraZones.detailTitle")}
      >
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold">
              {stallCode ?? t("cameraZones.noStall")}
            </span>
            {/*
             * ⚠ VERSIYA — `muted`, aksent EMAS (§10.3): u kontekst,
             *   e'tibor tortadigan holat emas. Saqlanmagan zonada
             *   badge UMUMAN chizilmaydi — «Versiya 0» degan son yo'q
             *   narsani bor deb ko'rsatardi.
             */}
            {version === null ? null : (
              <Badge tone="muted">{t("cameraZones.version", { version })}</Badge>
            )}
          </div>

          <Field id={searchId} label={t("cameraZones.stallSearch")}>
            <Input
              autoComplete="off"
              id={searchId}
              onChange={(event) => setQuery(event.target.value)}
              value={query}
            />
          </Field>

          {matches.length === 0 ? (
            <p className="text-sm text-text-muted">
              {t("cameraZones.noStallMatches")}
            </p>
          ) : (
            <ul className="flex max-h-64 flex-col gap-1 overflow-y-auto">
              {matches.map((match) => (
                <li key={match.id}>
                  <button
                    aria-current={match.id === stallId ? "true" : undefined}
                    className="flex min-h-11 w-full items-center justify-between gap-3 rounded-md px-3 text-left text-sm hover:bg-surface-muted"
                    onClick={() =>
                      onAssignStall({ code: match.code, id: match.id })
                    }
                    type="button"
                  >
                    <span className="font-mono font-semibold">{match.code}</span>
                    {/* Zona nomi — DB kontenti, tarjima qilinmaydi (D-16). */}
                    <span className="truncate text-text-muted">
                      {match.zoneName}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {/*
           * ⚠ `ghost` — destruktiv amal, lekin u TASDIQ SO'RAYDI
           *   (muharrirdagi DL-3) va bu yerda faqat uni ochadi. Qizil
           *   fon dialog ichida ikkinchi «asosiy» tugma yasardi.
           */}
          <Button
            className="self-start"
            onClick={onDelete}
            size="sm"
            variant="ghost"
          >
            {t("cameraZones.deleteZone")}
          </Button>

          <Dialog.Footer>
            <Dialog.Close asChild>
              <Button className="sm:flex-1" variant="secondary">
                {t("common.close")}
              </Button>
            </Dialog.Close>
          </Dialog.Footer>
        </div>
      </Dialog.Content>
    </Dialog.Root>
  );
}
