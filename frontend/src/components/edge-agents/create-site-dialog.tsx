"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { EDGE_SITE_KINDS } from "@/lib/api-types";
import type { EdgeActivationCode, EdgeSiteKind } from "@/lib/api-types";
import { errorMessageKey } from "@/lib/api-client";
import { useCreateEdgeSite } from "@/lib/edge-site-queries";

/** «Yangi obyekt»: tur + nom -> POST -> aktivatsiya kodi chaqiruvchiga. */
export function CreateSiteDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (code: EdgeActivationCode) => void;
}) {
  const t = useTranslations();
  const tKind = useTranslations("edgeAgents.kind");
  const create = useCreateEdgeSite();

  const [kind, setKind] = useState<EdgeSiteKind>("parking");
  const [name, setName] = useState("");
  const [nameError, setNameError] = useState<string | undefined>();

  function reset() {
    setKind("parking");
    setName("");
    setNameError(undefined);
  }

  function handleOpenChange(next: boolean) {
    if (!next) reset();
    onOpenChange(next);
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = name.trim();
    if (trimmed === "") {
      setNameError(t("edgeAgents.nameRequired"));
      return;
    }
    try {
      const created = await create.mutateAsync({ kind, name: trimmed });
      reset();
      onOpenChange(false);
      onCreated(created.activation_code);
    } catch (cause) {
      toast.error(t(errorMessageKey(cause)));
    }
  }

  return (
    <Dialog.Root onOpenChange={handleOpenChange} open={open}>
      <Dialog.Content
        description={t("edgeAgents.createDescription")}
        icon={Plus}
        title={t("edgeAgents.newSite")}
      >
        <form className="flex flex-col gap-4" noValidate onSubmit={(e) => void submit(e)}>
          <Field id="edge-site-kind" label={t("edgeAgents.fieldKind")}>
            <Select
              id="edge-site-kind"
              onChange={(event) => setKind(event.target.value as EdgeSiteKind)}
              value={kind}
            >
              {EDGE_SITE_KINDS.map((value) => (
                <option key={value} value={value}>
                  {tKind(value)}
                </option>
              ))}
            </Select>
          </Field>

          <Field
            error={nameError}
            id="edge-site-name"
            label={t("edgeAgents.fieldName")}
          >
            <Input
              aria-describedby={nameError ? "edge-site-name-error" : undefined}
              aria-invalid={nameError ? true : undefined}
              autoComplete="off"
              id="edge-site-name"
              maxLength={120}
              onChange={(event) => {
                setName(event.target.value);
                if (nameError) setNameError(undefined);
              }}
              value={name}
            />
          </Field>

          <Dialog.Footer>
            <Button
              className="sm:flex-1"
              disabled={create.isPending}
              type="submit"
            >
              {create.isPending ? t("common.loading") : t("edgeAgents.create")}
            </Button>
            <Dialog.Close asChild>
              <Button className="sm:flex-1" variant="secondary">
                {t("common.cancel")}
              </Button>
            </Dialog.Close>
          </Dialog.Footer>
        </form>
      </Dialog.Content>
    </Dialog.Root>
  );
}
