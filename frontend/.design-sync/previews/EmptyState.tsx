import { Button, EmptyState } from "sbozor-frontend";

export const NoShift = () => (
  <EmptyState
    action={<Button size="lg">Smenani ochish</Button>}
    description="Avval smenani ochish kerak"
    title="Ochiq smena yo'q"
  />
);

export const NoPayments = () => (
  <EmptyState
    description="Bu smenada to'lov yozilmagan"
    title="To'lovlar yo'q"
  />
);
