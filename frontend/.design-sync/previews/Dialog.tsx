import { Button, Dialog, Field, Input } from "sbozor-frontend";

/* Ochiq holat — karta ichida ko'rinishi uchun `open` qotirilgan. */
export const Open = () => (
  <Dialog.Root open>
    <Dialog.Content
      description="Yangi summa audit jurnaliga sabab bilan yoziladi."
      size="sm"
      title="Summani o'zgartirish"
    >
      <Field id="new-amount" label="Yangi summa">
        <Input
          className="min-h-14 font-mono tabular-nums"
          defaultValue="12000"
          id="new-amount"
          inputMode="numeric"
        />
      </Field>
      <Dialog.Footer>
        <Button>Saqlash</Button>
        <Button variant="secondary">Bekor qilish</Button>
      </Dialog.Footer>
    </Dialog.Content>
  </Dialog.Root>
);
