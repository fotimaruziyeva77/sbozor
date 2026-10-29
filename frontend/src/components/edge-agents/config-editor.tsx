"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { isPlainObject } from "@/components/edge-agents/edge-labels";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { EdgeConfig, EdgeConfigIssue } from "@/lib/api-types";
import { ApiError, errorMessageKey } from "@/lib/api-client";
import {
  edgeConfigIssuesOf,
  useEdgeConfigQuery,
  useSaveEdgeConfig,
} from "@/lib/edge-site-queries";

function pretty(doc: Record<string, unknown>): string {
  return JSON.stringify(doc, null, 2);
}

/** Sozlama muharriri: GET config -> JSON matn -> PUT. */
export function ConfigEditor({
  siteId,
  canManage,
}: {
  siteId: string;
  canManage: boolean;
}) {
  const t = useTranslations();
  const config = useEdgeConfigQuery(siteId);

  return (
    <Card>
      <CardHeader>
        <h2 className="text-lg font-semibold">{t("edgeAgents.config.title")}</h2>
        <p className="text-sm text-text-muted">{t("edgeAgents.config.hint")}</p>
      </CardHeader>
      <CardContent>
        {config.isPending ? (
          <div aria-busy="true" role="status">
            <span className="sr-only">{t("common.loading")}</span>
            <Skeleton className="h-64" />
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
          /*
           * `key` — saqlangan versiya o'zgarsa matn yangi hujjatdan
           * qayta boshlanadi; tahrir paytidagi fon yangilanishi esa
           * (`refetchOnWindowFocus: false`) matnni bosib ketmaydi.
           */
          <ConfigForm
            canManage={canManage}
            config={config.data}
            key={config.data.version}
            siteId={siteId}
          />
        )}
      </CardContent>
    </Card>
  );
}

function ConfigForm({
  siteId,
  config,
  canManage,
}: {
  siteId: string;
  config: EdgeConfig;
  canManage: boolean;
}) {
  const t = useTranslations();
  const save = useSaveEdgeConfig(siteId);
  const [text, setText] = useState(() => pretty(config.doc));
  const [localError, setLocalError] = useState<string | null>(null);
  const [issues, setIssues] = useState<EdgeConfigIssue[]>([]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIssues([]);

    let parsed: unknown;
    try {
      parsed = JSON.parse(text);
    } catch {
      setLocalError(t("edgeAgents.config.invalidJson"));
      return;
    }
    if (!isPlainObject(parsed)) {
      setLocalError(t("edgeAgents.config.notObject"));
      return;
    }
    setLocalError(null);

    try {
      const saved = await save.mutateAsync(parsed);
      toast.success(t("edgeAgents.config.saved", { version: saved.version }));
    } catch (cause) {
      const serverIssues = edgeConfigIssuesOf(cause);
      if (serverIssues !== null) {
        setIssues(serverIssues);
        return;
      }
      if (cause instanceof ApiError && cause.detail === "config_not_object") {
        setLocalError(t("edgeAgents.config.notObject"));
        return;
      }
      toast.error(t(errorMessageKey(cause)));
    }
  }

  const errorId = "edge-config-error";
  const hasError = localError !== null || issues.length > 0;

  return (
    <form className="flex flex-col gap-3" noValidate onSubmit={(e) => void submit(e)}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label className="text-sm font-semibold" htmlFor="edge-config-text">
          {t("edgeAgents.config.label")}
        </label>
        <span className="text-xs text-text-muted">
          {t("edgeAgents.config.version", { version: config.version })}
        </span>
      </div>
      <textarea
        aria-describedby={hasError ? errorId : undefined}
        aria-invalid={hasError ? true : undefined}
        className="min-h-80 w-full rounded-sm border border-border-ui bg-surface p-3 font-mono text-xs text-text outline-none focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-accent/25 aria-[invalid=true]:border-danger"
        id="edge-config-text"
        onChange={(event) => {
          setText(event.target.value);
          if (localError !== null) setLocalError(null);
        }}
        readOnly={!canManage}
        spellCheck={false}
        value={text}
      />

      {localError !== null ? (
        <p className="text-sm text-danger-text" id={errorId} role="alert">
          {localError}
        </p>
      ) : null}

      {issues.length > 0 ? (
        <div
          className="rounded-md bg-danger/10 p-3 text-sm text-danger-text"
          id={errorId}
          role="alert"
        >
          <p className="font-semibold">{t("edgeAgents.config.errorsTitle")}</p>
          <ul className="mt-2 flex list-disc flex-col gap-1 pl-5">
            {issues.map((issue, index) => (
              <li key={`${issue.path}-${index}`}>
                <span className="font-mono">
                  {issue.path === "" ? t("edgeAgents.config.rootPath") : issue.path}
                </span>
                {": "}
                {issue.message}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {canManage ? (
        <div className="flex flex-wrap gap-2">
          <Button disabled={save.isPending} type="submit">
            {save.isPending ? t("common.loading") : t("edgeAgents.config.save")}
          </Button>
          <Button
            onClick={() => {
              setText(pretty(config.doc));
              setLocalError(null);
              setIssues([]);
            }}
            variant="secondary"
          >
            {t("edgeAgents.config.reset")}
          </Button>
        </div>
      ) : null}
    </form>
  );
}
