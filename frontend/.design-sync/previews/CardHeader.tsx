import { Card, CardContent, CardHeader } from "sbozor-frontend";

/* CardHeader yolg'iz turmaydi — u Card ning yuqori qismi. */
export const InCard = () => (
  <Card>
    <CardHeader>
      <h3 className="text-lg font-semibold">Kunlik hisobot</h3>
      <p className="text-sm text-text-muted">15-avgust · Karmana bozori</p>
    </CardHeader>
    <CardContent>
      <p className="text-sm text-text-muted">Band rastalar: 215 · To'langan: 214</p>
    </CardContent>
  </Card>
);
