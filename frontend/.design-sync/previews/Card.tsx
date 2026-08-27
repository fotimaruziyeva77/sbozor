import { Badge, Button, Card, CardContent, CardHeader } from "sbozor-frontend";

export const Basic = () => (
  <Card>
    <CardHeader>
      <h3 className="text-lg font-semibold">Kutilayotgan patta</h3>
      <p className="text-sm text-text-muted">Bu kutilayotgan summa — hisob hali yozilmagan.</p>
    </CardHeader>
    <CardContent className="flex flex-col items-start gap-3">
      <p className="font-mono text-2xl font-semibold tabular-nums">8 000 so'm</p>
      <Badge tone="success">Qarzi yo'q</Badge>
    </CardContent>
  </Card>
);

export const WithAction = () => (
  <Card>
    <CardHeader>
      <p className="text-xs font-semibold tracking-wide text-text-muted uppercase">Boshlangan vaqt</p>
      <p className="text-lg font-semibold tabular-nums">15-avgust, 06:45</p>
    </CardHeader>
    <CardContent>
      <Button className="w-full" size="lg">Smenani yopish</Button>
    </CardContent>
  </Card>
);
