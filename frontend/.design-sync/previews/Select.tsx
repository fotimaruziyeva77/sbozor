import { Select } from "sbozor-frontend";

export const Basic = () => (
  <div className="w-80">
    <Select defaultValue="cash">
      <option value="cash">Naqd</option>
      <option value="terminal">Terminal</option>
    </Select>
  </div>
);

export const Reasons = () => (
  <div className="w-80">
    <Select defaultValue="">
      <option disabled value="">Sabab tanlang</option>
      <option value="wrong_stall">Rasta xato tanlangan</option>
      <option value="wrong_amount">Summa xato</option>
      <option value="duplicate_entry">Takroriy yozuv</option>
    </Select>
  </div>
);
