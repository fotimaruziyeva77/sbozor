"use client";

import { useId, useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import {
  EXEMPT_MAX,
  LABEL_MAX,
  exemptPlatesOf,
  isPlateValid,
  normalizePlate,
  withExemptPlates,
} from "@/components/parking/exempt-plates";
import type { ExemptPlate } from "@/components/parking/exempt-plates";
import { PLATE_EXAMPLE } from "@/components/parking/parking-data";
import { PlateBadge } from "@/components/parking/plate-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import type { EdgeConfig } from "@/lib/api-types";
import { ApiError, errorMessageKey } from "@/lib/api-client";
import { useAuthStore } from "@/lib/auth-store";
import {
  edgeConfigIssuesOf,
  useEdgeConfigQuery,
  useSaveEdgeConfig,
} from "@/lib/edge-site-queries";
import { hasPermission } from "@/lib/rbac";

/*
 * =============================================================================
 * PUL OLINMAYDIGAN MASHINALAR — obyekt sozlamasidagi `parking.exempt_plates`
 * ro'yxatini ko'rish va o'zgartirish.
 *
 * Ro'yxat AGENTDA EMAS, SERVERDA yashaydi (agent «bo'sh» keladi, biznes
 * mantiq serverda): har qo'shish/olib tashlash — sozlamaning YANGI
 * versiyasi (`PUT /edge-sites/{id}/config`, append-only, auditga tushadi).
 * Agent uni keyingi poll'da oladi — odatda bir daqiqa ichida.
 *
 * Kim o'zgartiradi: `camera_manage` (bozor admini). Direktor (`camera_view`)
 * ro'yxatni KO'RADI, lekin forma va tugmalar chiqmaydi — pul olinmaslik
 * huquqi kassir yoki direktor qo'lida bo'lmasin (tushum «oqib» ketmasin).
 *
 * ⛔ Hujjat nusxasi holatda SAQLANMAYDI: har amal so'rov javobidagi
 *    hujjatdan hisoblanadi, saqlangach javob keshga yoziladi
 *    (`useSaveEdgeConfig.onSuccess`). Ikki brauzer bir vaqtda saqlasa server
 *    409 beradi — ro'yxat qayta o'qiladi va foydalanuvchiga aytiladi.
 * =============================================================================
 */
export function ExemptPlatesCard({ siteId }: { siteId: string }) {
  const t = useTranslations();
  const { principal } = useAuthStore();
  const canManage = hasPermission(principal?.roles ?? [], "camera_manage");
  const config = useEdgeConfigQuery(siteId);

  return (
    <Card>
      <CardHeader>
        <h2 className="text-lg font-semibold">{t("parkingReport.exempt.title")}</h2>
        <p className="text-sm text-text-muted">{t("parkingReport.exempt.hint")}</p>
      </CardHeader>
      <CardContent>
        {config.isPending ? (
          <div aria-busy="true" role="status">
            <span className="sr-only">{t("common.loading")}</span>
            <Skeleton className="h-32" />
          </div>
        ) : config.isError ? (
          <div
            className="flex flex-col items-start gap-3 rounded-md bg-danger/10 p-4 text-danger-text"
            role="alert"
          >
            <p className="text-sm">{t("errors.loadFailedBody")}</p>
            <Button onClick={() => void config.refetch()} size="sm" variant="secondary">
              {t("common.retry")}
            </Button>
          </div>
        ) : (
          <ExemptPlatesBody
            canManage={canManage}
            config={config.data}
            onReload={() => void config.refetch()}
            siteId={siteId}
          />
        )}
      </CardContent>
    </Card>
  );
}

function ExemptPlatesBody({
  siteId,
  config,
  canManage,
  onReload,
}: {
  siteId: string;
  config: EdgeConfig;
  canManage: boolean;
  onReload: () => void;
}) {
  const t = useTranslations();
  const save = useSaveEdgeConfig(siteId);
  const plateId = useId();
  const labelId = useId();
  const [plateText, setPlateText] = useState("");
  const [labelText, setLabelText] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [removing, setRemoving] = useState<ExemptPlate | null>(null);

  const list = exemptPlatesOf(config.doc);

  /** Saqlash xatosini odam tiliga o'giradi; 409 — ro'yxat qayta o'qiladi. */
  function explain(cause: unknown): string {
    const issues = edgeConfigIssuesOf(cause);
    if (issues !== null && issues.length > 0) {
      return issues.map((issue) => issue.message).join(" ");
    }
    if (cause instanceof ApiError && cause.status === 409) {
      onReload();
      return t("parkingReport.exempt.conflict");
    }
    return t(errorMessageKey(cause));
  }

  async function add(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const plate = normalizePlate(plateText);
    const label = labelText.trim();
    if (!isPlateValid(plate)) {
      setFormError(t("parkingReport.exempt.errPlate"));
      return;
    }
    if (list.some((item) => item.plate === plate)) {
      setFormError(t("parkingReport.exempt.errDuplicate"));
      return;
    }
    if (label.length > LABEL_MAX) {
      setFormError(t("parkingReport.exempt.errLabel"));
      return;
    }
    if (list.length >= EXEMPT_MAX) {
      setFormError(t("parkingReport.exempt.errFull"));
      return;
    }
    setFormError(null);
    const next: ExemptPlate = label === "" ? { plate } : { plate, label };
    try {
      const saved = await save.mutateAsync(withExemptPlates(config.doc, [...list, next]));
      toast.success(t("parkingReport.exempt.saved", { version: saved.version }));
      setPlateText("");
      setLabelText("");
    } catch (cause) {
      setFormError(explain(cause));
    }
  }

  async function remove(item: ExemptPlate) {
    try {
      const saved = await save.mutateAsync(
        withExemptPlates(
          config.doc,
          list.filter((other) => other.plate !== item.plate),
        ),
      );
      toast.success(t("parkingReport.exempt.saved", { version: saved.version }));
    } catch (cause) {
      toast.error(explain(cause));
    } finally {
      setRemoving(null);
    }
  }

  const errorId = `${plateId}-error`;

  return (
    <div className="flex flex-col gap-5">
      {canManage ? (
        <form
          className="flex flex-col gap-3 sm:flex-row sm:items-start"
          noValidate
          onSubmit={(event) => void add(event)}
        >
          <Field
            className="sm:w-56"
            error={formError ?? undefined}
            hint={t("parkingReport.exempt.plateHint", { example: PLATE_EXAMPLE })}
            id={plateId}
            label={t("parkingReport.exempt.plateLabel")}
          >
            <Input
              aria-describedby={formError !== null ? errorId : `${plateId}-hint`}
              aria-invalid={formError !== null ? true : undefined}
              autoCapitalize="characters"
              autoComplete="off"
              className="font-mono uppercase"
              id={plateId}
              maxLength={16}
              onChange={(event) => {
                setPlateText(event.target.value);
                if (formError !== null) setFormError(null);
              }}
              value={plateText}
            />
          </Field>
          <Field
            className="sm:flex-1"
            hint={t("parkingReport.exempt.labelHint")}
            id={labelId}
            label={t("parkingReport.exempt.labelLabel")}
          >
            <Input
              aria-describedby={`${labelId}-hint`}
              autoComplete="off"
              id={labelId}
              maxLength={LABEL_MAX}
              onChange={(event) => setLabelText(event.target.value)}
              value={labelText}
            />
          </Field>
          <Button className="sm:mt-7" disabled={save.isPending} type="submit">
            {save.isPending ? t("common.loading") : t("parkingReport.exempt.add")}
          </Button>
        </form>
      ) : (
        <p className="text-sm text-text-muted">{t("parkingReport.exempt.readOnly")}</p>
      )}

      {list.length === 0 ? (
        <div className="rounded-md bg-surface-muted p-4 text-sm">
          <p className="font-semibold">{t("parkingReport.exempt.empty")}</p>
          {canManage ? (
            <p className="text-text-muted">{t("parkingReport.exempt.emptyHint")}</p>
          ) : null}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <caption className="sr-only">{t("parkingReport.exempt.title")}</caption>
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-muted">
                <th className="p-2 font-normal" scope="col">
                  {t("parkingReport.exempt.colPlate")}
                </th>
                <th className="p-2 font-normal" scope="col">
                  {t("parkingReport.exempt.colLabel")}
                </th>
                {canManage ? (
                  <th className="p-2" scope="col">
                    <span className="sr-only">{t("parkingReport.exempt.remove")}</span>
                  </th>
                ) : null}
              </tr>
            </thead>
            <tbody>
              {list.map((item) => (
                <tr
                  className="border-b border-border transition-colors last:border-b-0 hover:bg-surface-muted"
                  key={item.plate}
                >
                  <td className="p-2">
                    <PlateBadge plate={item.plate} size="sm" />
                  </td>
                  <td className="p-2">{item.label ?? "—"}</td>
                  {canManage ? (
                    <td className="p-2 text-right">
                      <Button
                        aria-label={`${t("parkingReport.exempt.remove")}: ${item.plate}`}
                        disabled={save.isPending}
                        onClick={() => setRemoving(item)}
                        size="sm"
                        variant="ghost"
                      >
                        {t("parkingReport.exempt.remove")}
                      </Button>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-xs text-text-muted">
        {t("parkingReport.exempt.count", { count: list.length })}
      </p>

      <ConfirmDialog
        cancelLabel={t("common.cancel")}
        confirmLabel={t("parkingReport.exempt.remove")}
        confirmVariant="destructive"
        description={t("parkingReport.exempt.removeDescription", {
          plate: removing?.plate ?? "",
        })}
        isBusy={save.isPending}
        onConfirm={() => {
          if (removing !== null) void remove(removing);
        }}
        onOpenChange={(open) => {
          if (!open && !save.isPending) setRemoving(null);
        }}
        open={removing !== null}
        title={t("parkingReport.exempt.removeTitle")}
      />
    </div>
  );
}
