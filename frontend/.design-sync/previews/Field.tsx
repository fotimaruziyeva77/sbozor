import { Field, Input, Select } from "sbozor-frontend";

export const WithHint = () => (
  <div className="w-80">
    <Field hint="Raqamni kiritib «Enter» bosing" id="stall" label="Rasta raqami">
      <Input id="stall" inputMode="numeric" placeholder="A-01" />
    </Field>
  </div>
);

export const WithError = () => (
  <div className="w-80">
    <Field error="Summani faqat raqam bilan kiriting" id="declared" label="Yig'ilgan naqd">
      <Input aria-invalid id="declared" defaultValue="8 000!" inputMode="numeric" />
    </Field>
  </div>
);

export const WithSelect = () => (
  <div className="w-80">
    <Field id="reason" label="O'zgartirish sababi">
      <Select id="reason" defaultValue="tariff_correction">
        <option value="late_review">Kech ko'rib chiqildi</option>
        <option value="tariff_correction">Tarif tuzatildi</option>
        <option value="director_waiver">Direktor ruxsati</option>
      </Select>
    </Field>
  </div>
);
