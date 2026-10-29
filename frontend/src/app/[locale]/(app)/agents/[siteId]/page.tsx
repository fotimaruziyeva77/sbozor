"use client";

import { useParams } from "next/navigation";

import { ForbiddenNotice } from "@/components/auth/forbidden-notice";
import { SiteDetail } from "@/components/edge-agents/site-detail";
import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";

/*
 * Bitta obyekt: agent holati, sozlama, buyruqlar, hodisalar.
 * Sarlavha (`<title>`) `agents/layout.tsx` dan meros — u bola
 * marshrutlarni ham qamraydi.
 */
export default function AgentSitePage() {
  const { principal } = useAuthStore();
  const params = useParams<{ siteId: string }>();
  const roles = principal?.roles ?? [];

  if (!hasPermission(roles, "camera_view")) {
    return <ForbiddenNotice />;
  }

  return (
    <SiteDetail
      canManage={hasPermission(roles, "camera_manage")}
      key={params.siteId}
      siteId={params.siteId}
    />
  );
}
