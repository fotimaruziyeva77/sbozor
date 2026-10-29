import { describe, expect, test } from "vitest";

import {
  agentState,
  commandState,
  eventTypeLabel,
  gateLanes,
  isPlainObject,
  summarizeEventData,
} from "@/components/edge-agents/edge-labels";
import type { EdgeCommand, EdgeSite } from "@/lib/api-types";

function site(overrides: Partial<EdgeSite> = {}): EdgeSite {
  return {
    id: "s1",
    kind: "parking",
    name: "Karmana",
    created_at: "2026-10-30T06:00:00+05:00",
    config_version: 1,
    setup: { devices: [], lanes: [] },
    agent: null,
    ...overrides,
  };
}

const agent = {
  id: "a1",
  hostname: "pc",
  version: "1.0.0",
  os: "windows",
  last_seen_at: "2026-10-30T06:00:00+05:00",
  online: true,
  heartbeat: null,
};

describe("edge-labels", () => {
  test("agent holati: ulanmagan / onlayn / oflayn", () => {
    expect(agentState(site())).toBe("never");
    expect(agentState(site({ agent: { ...agent, last_seen_at: null } }))).toBe("never");
    expect(agentState(site({ agent }))).toBe("online");
    expect(agentState(site({ agent: { ...agent, online: false } }))).toBe("offline");
  });

  test("shlagbaum faqat `parking` yoki turi yo'q yo'laklarda", () => {
    const lanes = gateLanes(
      site({
        setup: {
          devices: [],
          lanes: [
            { id: "l1", direction: "in", mode: "auto" },
            { id: "l2", direction: "out", mode: "auto", kind: "parking" },
            { id: "l3", direction: "in", mode: "manual", kind: "livestock" },
          ],
        },
      }),
    );
    expect(lanes.map((lane) => lane.id)).toEqual(["l1", "l2"]);
  });

  test("buyruq holati: natija > yetkazildi > kutilmoqda", () => {
    const base: EdgeCommand = {
      id: "c1",
      type: "core.config.refresh",
      data: {},
      issued_by: "u",
      issued_at: "2026-10-30T06:00:00+05:00",
      expires_at: "2026-10-30T06:10:00+05:00",
      delivered_at: null,
      result_status: null,
      result_reason: null,
      result_at: null,
    };
    expect(commandState(base)).toBe("pending");
    expect(commandState({ ...base, delivered_at: base.issued_at })).toBe("delivered");
    expect(commandState({ ...base, result_status: "rejected" })).toBe("rejected");
  });

  test("noma'lum hodisa turi `null` — xom tur ko'rsatiladi", () => {
    expect(eventTypeLabel("parking.plate.read")).toBe("plateRead");
    expect(eventTypeLabel("toString")).toBeNull();
    expect(eventTypeLabel("x.y.z")).toBeNull();
  });

  test("hodisa tafsiloti: oddiy qiymatlar, pul formatlanadi, obyektlar tashlanadi", () => {
    const text = summarizeEventData(
      { plate: "01A123BC", amount_soum: 5000, nested: { a: 1 }, ok: true },
      (value) => `${value} so'm`,
    );
    expect(text).toBe("plate: 01A123BC · amount_soum: 5000 so'm · ok: true");
    expect(summarizeEventData({ long: "x".repeat(300) }, String, 20)).toHaveLength(20);
  });

  test("sozlama faqat obyekt bo'lishi mumkin", () => {
    expect(isPlainObject({})).toBe(true);
    expect(isPlainObject([])).toBe(false);
    expect(isPlainObject(null)).toBe(false);
    expect(isPlainObject("x")).toBe(false);
  });
});
