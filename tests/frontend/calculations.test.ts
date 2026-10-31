import { describe, expect, it } from "vitest";
import { compute, type TrackerState } from "../../assets/src/calculations.ts";

const state: TrackerState = {
  year: 2026,
  limit: 5300,
  rate: 2,
  base: 1000,
  bonus13: 1000,
  bonus14: 500,
  months: { 5: { employee: 20, employer: 30 } },
  voluntary: [{ date: "01/05/2026", amount: 100 }],
};

describe("compute", () => {
  it("totals contributions and estimates future months including bonuses", () => {
    expect(compute(state)).toMatchObject({
      employee: 20,
      employer: 30,
      voluntary: 100,
      total: 150,
      remaining: 5150,
      estimates: { 6: 30, 12: 40 },
      estimateTotal: 170,
      remainingAtYearEnd: 4980,
      lastMonth: 5,
    });
  });

  it("does not estimate future contributions without a month or required inputs", () => {
    expect(compute({ ...state, months: {} }).estimateTotal).toBe(0);
    expect(compute({ ...state, rate: 0 }).estimates).toEqual({});
    expect(compute({ ...state, base: 0 }).estimates).toEqual({});
  });

  it("calculates excess values without changing the state", () => {
    const overLimit = { ...state, limit: 100 };
    expect(compute(overLimit).remaining).toBe(-50);
    expect(state.limit).toBe(5300);
  });
});
