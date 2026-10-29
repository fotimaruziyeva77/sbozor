"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";

import { ForbiddenNotice } from "@/components/auth/forbidden-notice";
import { ActivationCodeDialog } from "@/components/edge-agents/activation-code-dialog";
import { CreateSiteDialog } from "@/components/edge-agents/create-site-dialog";
import { SiteList } from "@/components/edge-agents/site-list";
import { Button } from "@/components/ui/button";
import type { EdgeActivationCode } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";

/*
 * «Agentlar» — bozor / avtoturargoh / mol bozoridagi universal agentlar.
 *
 * Sahifa `camera_view` bilan ochiladi (ro'yxat marshruti shu huquqni
 * talab qiladi); «Yangi obyekt» va boshqa o'zgartiruvchi amallar —
 * `camera_manage`. Menyu yozuvi esa faqat `camera_manage` da ko'rinadi
 * (`app-shell.tsx`). Haqiqiy darvoza — serverdagi `require_permission`.
 */
export default function AgentsPage() {
  const t = useTranslations();
  const { principal } = useAuthStore();
  const roles = principal?.roles ?? [];
  const [creating, setCreating] = useState(false);
  const [code, setCode] = useState<EdgeActivationCode | null>(null);

  if (!hasPermission(roles, "camera_view")) {
    return <ForbiddenNotice />;
  }

  const canManage = hasPermission(roles, "camera_manage");

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight">
            {t("edgeAgents.title")}
          </h1>
          <p className="text-sm text-text-muted">{t("edgeAgents.subtitle")}</p>
        </div>
        {canManage ? (
          <Button onClick={() => setCreating(true)}>
            <Plus aria-hidden="true" />
            {t("edgeAgents.newSite")}
          </Button>
        ) : null}
      </div>

      <SiteList />

      {canManage ? (
        <CreateSiteDialog
          onCreated={setCode}
          onOpenChange={setCreating}
          open={creating}
        />
      ) : null}
      <ActivationCodeDialog code={code} onClose={() => setCode(null)} />
    </div>
  );
}
