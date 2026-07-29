import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

/*
 * VAQTINCHALIK ildiz sahifa — dizayn primitivlarining quriladiganini
 * isbotlaydi. 2-taskda `app/[locale]/page.tsx` bilan almashtiriladi.
 */
export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center gap-4 p-6">
      <Card>
        <CardHeader>
          <h1 className="text-xl font-semibold tracking-tight">SBOZOR</h1>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <Input placeholder="+998" />
          <Button size="lg">OK</Button>
        </CardContent>
      </Card>
    </main>
  );
}
