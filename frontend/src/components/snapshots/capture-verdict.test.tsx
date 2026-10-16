/**
 * Kadr olish holati banneri (261016) — «kameralar ishlayaptimi?» degan
 * savolga bitta jumlali javob.
 *
 * ⛔ Hisob matritsa bilan AYNI holat funksiyasidan: banner muammoli degan
 *    kamera jadvalda ham muammoli. «Oxirgi kadr» faqat bugun uchun.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import {
  CaptureVerdictBanner,
  cameraHealth,
  captureVerdict,
} from "@/components/snapshots/capture-verdict";
import type { CaptureRun } from "@/lib/api-types";

const CAM_A = "70000000-0000-4000-8000-000000000001";
const CAM_B = "70000000-0000-4000-8000-000000000002";
const CAM_C = "70000000-0000-4000-8000-000000000003";

let seq = 0;
function run(
  camera: string,
  slot: string,
  status: string,
  verdict: string | null = null,
  name = "Kirish",
): CaptureRun {
  seq += 1;
  return {
    run_id: `81000000-0000-4000-8000-${String(seq).padStart(12, "0")}`,
    camera_id: camera,
    channel_no: 1,
    camera_name: name,
    slot_time: slot,
    scheduled_at: "2026-10-16T01:00:00Z",
    status,
    attempts: status === "pending" ? 0 : 1,
    error_code: null,
    quality_verdict: verdict,
    snapshot_id: null,
  };
}

function renderBanner(
  rows: CaptureRun[],
  options: { isToday?: boolean; newestCaptureAt?: string | null; onShowIssues?: () => void } = {},
) {
  return render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      now={new Date("2026-10-16T09:00:00Z")}
      timeZone="Asia/Tashkent"
    >
      <CaptureVerdictBanner
        cameraMeta={
          new Map([
            [CAM_A, { ip: "192.168.1.101" }],
            [CAM_B, { ip: "192.168.1.102" }],
            [CAM_C, { ip: "192.168.1.103" }],
          ])
        }
        isToday={options.isToday ?? true}
        newestCaptureAt={options.newestCaptureAt ?? null}
        onShowIssues={options.onShowIssues ?? (() => undefined)}
        rows={rows}
      />
    </NextIntlClientProvider>,
  );
}

describe("cameraHealth — matritsa qatori bilan bir xil hisob", () => {
  test("holatlar to'rt guruhga ajraladi, rejaga kirmagani sanalmaydi", () => {
    const [health] = cameraHealth([
      run(CAM_A, "06:00:00", "succeeded", "ok"),
      run(CAM_A, "07:00:00", "succeeded", "dark"),
      run(CAM_A, "08:00:00", "failed"),
      run(CAM_A, "09:00:00", "missed"),
      run(CAM_A, "10:00:00", "pending"),
      run(CAM_A, "11:00:00", "skipped"),
    ]);
    expect(health).toMatchObject({ ok: 1, poor: 1, lost: 2, pending: 1 });
  });
});

describe("captureVerdict", () => {
  test("qator yo'q — banner yo'q", () => {
    expect(captureVerdict([])).toBeNull();
  });

  test("bitta ham kadr kelmagan, yo'qolgani bor — «down»", () => {
    expect(
      captureVerdict([
        run(CAM_A, "06:00:00", "missed"),
        run(CAM_B, "06:00:00", "failed"),
        run(CAM_A, "07:00:00", "pending"),
      ]),
    ).toEqual({ kind: "down", lost: 2 });
  });

  test("ba'zi kameralarda muammo — eng ko'p yo'qolgani birinchi", () => {
    const verdict = captureVerdict([
      run(CAM_A, "06:00:00", "succeeded", "ok"),
      run(CAM_B, "06:00:00", "succeeded", "dark"),
      run(CAM_C, "06:00:00", "missed"),
    ]);
    expect(verdict?.kind).toBe("issues");
    if (verdict?.kind !== "issues") return;
    expect(verdict.cameras).toBe(3);
    expect(verdict.problems.map((camera) => camera.cameraId)).toEqual([CAM_C, CAM_B]);
  });

  test("hammasi yaroqli — «ok» va keyingi vaqt", () => {
    expect(
      captureVerdict([
        run(CAM_A, "06:00:00", "succeeded", "ok"),
        run(CAM_A, "08:00:00", "pending"),
        run(CAM_A, "07:00:00", "pending"),
      ]),
    ).toEqual({ kind: "ok", cameras: 1, next: "07:00", ok: 1 });
  });

  test("hali hech narsa olinmagan va yo'qolmagan — «waiting»", () => {
    expect(
      captureVerdict([run(CAM_A, "06:00:00", "pending"), run(CAM_B, "06:00:00", "running")]),
    ).toEqual({ kind: "waiting", cameras: 2, next: "06:00" });
  });
});

describe("CaptureVerdictBanner", () => {
  const down = [run(CAM_A, "06:00:00", "missed"), run(CAM_B, "06:00:00", "missed")];

  test("bugun kadr yo'q — sarlavha, son va oxirgi kadr vaqti", () => {
    renderBanner(down, { newestCaptureAt: "2026-10-11T08:00:00Z" });

    expect(
      screen.getByRole("heading", { name: messages.snapshots.verdictDownToday }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(messages.snapshots.verdictDownBody.replace("{count}", "2")),
    ).toBeInTheDocument();
    expect(screen.getByText(/11-oktabr, 2026 · 13:00/u)).toBeInTheDocument();
    expect(screen.getByText(/5 kun oldin/u)).toBeInTheDocument();
  });

  test("⛔ o'tgan kun ko'rilsa «oxirgi kadr» chiqmaydi — u HOZIRGI holat", () => {
    renderBanner(down, { isToday: false, newestCaptureAt: "2026-10-11T08:00:00Z" });

    expect(
      screen.getByRole("heading", { name: messages.snapshots.verdictDownDay }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/11-oktabr/u)).toBeNull();
  });

  test("muammoli kameralar nomi bilan; bir xil nomlilar IP bilan ajraladi", () => {
    const onShowIssues = vi.fn();
    renderBanner(
      [
        run(CAM_A, "06:00:00", "missed", null, "Camera 01"),
        run(CAM_B, "06:00:00", "succeeded", "ok", "Camera 01"),
        run(CAM_C, "06:00:00", "succeeded", "ok", "Kirish 2"),
      ],
      { onShowIssues },
    );

    expect(
      screen.getByRole("heading", {
        name: messages.snapshots.verdictIssuesTitle
          .replace("{total}", "3")
          .replace("{count}", "1"),
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Camera 01 · 192.168.1.101")).toBeInTheDocument();
    expect(
      screen.getByText(messages.snapshots.verdictCameraLost.replace("{count}", "1")),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: messages.snapshots.verdictShowIssues }));
    expect(onShowIssues).toHaveBeenCalledTimes(1);
  });

  test("hammasi joyida — yashil sarlavha, tugma yo'q", () => {
    renderBanner([run(CAM_A, "06:00:00", "succeeded", "ok"), run(CAM_A, "07:00:00", "pending")]);

    expect(
      screen.getByRole("heading", { name: messages.snapshots.verdictOkToday }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(messages.snapshots.verdictNext.replace("{time}", "07:00")),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });
});
