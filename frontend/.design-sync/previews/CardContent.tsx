import { Badge, Card, CardContent, CardHeader } from "sbozor-frontend";

/* CardContent yolg'iz turmaydi — u Card ning tanasi. */
export const InCard = () => (
  <Card>
    <CardHeader>
      <h3 className="text-lg font-semibold">Rasta A-01</h3>
    </CardHeader>
    <CardContent className="flex flex-col items-start gap-3">
      <p className="font-mono text-2xl font-semibold tabular-nums">8 000 so'm</p>
      <div className="flex gap-2">
        <Badge tone="success">To'langan</Badge>
        <Badge tone="muted">Naqd</Badge>
      </div>
    </CardContent>
  </Card>
);
