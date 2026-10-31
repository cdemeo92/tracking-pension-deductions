import { beforeEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  createTracker,
  type TrackerDependencies,
} from "../../assets/src/tracker.ts";
import type { TrackerState } from "../../assets/src/calculations.ts";
import type { ParsedPayslip } from "../../assets/src/payslip.ts";

const template = readFileSync(
  resolve(process.cwd(), "assets/template.html"),
  "utf8",
);
const body = template.match(/<body>([\s\S]*?)<\/body>/i)?.[1] ?? "";
const initialState: TrackerState = {
  year: 2026,
  limit: 5300,
  rate: 0,
  base: 0,
  bonus13: 0,
  bonus14: 0,
  months: {},
  voluntary: [],
};

function mountTracker(options: Partial<TrackerDependencies> = {}) {
  document.body.innerHTML = body;
  const app = createTracker({
    document,
    initialState,
    clipboard: { writeText: vi.fn(async () => undefined) },
    parsePayslip: vi
      .fn<TrackerDependencies["parsePayslip"]>()
      .mockResolvedValue({
        months: {},
        otherYears: [],
      }),
    onSave: vi.fn(async () => true),
    ...options,
  });
  return { app, document };
}

describe("createTracker", () => {
  beforeEach(() => vi.clearAllMocks());

  it("supports adding, editing and deleting months and voluntary payments", () => {
    const { app, document } = mountTracker();
    const monthPicker = document.getElementById(
      "newMonth",
    ) as HTMLSelectElement;
    monthPicker.value = "9";
    document.getElementById("addMonth")!.click();
    expect(app.state.months[9]).toEqual({ employee: 0, employer: 0 });

    const employeeInput = document.querySelector<HTMLInputElement>(
      '[data-month="9"][data-field="employee"]',
    )!;
    employeeInput.value = "12.5";
    employeeInput.dispatchEvent(
      new document.defaultView!.Event("change", { bubbles: true }),
    );
    expect(app.state.months[9].employee).toBe(12.5);

    document
      .querySelector<HTMLButtonElement>('[data-delete-month="9"]')!
      .click();
    expect(app.state.months[9]).toBeUndefined();

    document.getElementById("addVoluntary")!.click();
    const amountInput = document.querySelector<HTMLInputElement>(
      '[data-vol="0"][data-field="amount"]',
    )!;
    amountInput.value = "75";
    amountInput.dispatchEvent(
      new document.defaultView!.Event("change", { bubbles: true }),
    );
    expect(app.state.voluntary[0].amount).toBe(75);
    document.querySelector<HTMLButtonElement>('[data-delete-vol="0"]')!.click();
    expect(app.state.voluntary).toEqual([]);
  });

  it("does not add a payslip when employee and employer totals mismatch", async () => {
    const parsed: ParsedPayslip = {
      months: {
        1: {
          total: 91,
          employee: 23.57,
          employer: 66.43,
          hasTotal: true,
          hasRows: true,
        },
      },
      otherYears: [],
    };
    const parsePayslip = vi
      .fn<TrackerDependencies["parsePayslip"]>()
      .mockResolvedValue(parsed);
    const { app, document } = mountTracker({ parsePayslip });
    const file = new File([], "cedolino.pdf", { type: "application/pdf" });

    await app.handleFiles([file]);

    expect(app.state.months[1]).toBeUndefined();
    expect(document.getElementById("log")!.textContent).toContain(
      "non coincide",
    );
  });

  it("imports valid payslips and reports when the split is missing", async () => {
    const parsed: ParsedPayslip = {
      months: {
        1: {
          total: 90,
          employee: 23.57,
          employer: 66.43,
          hasTotal: true,
          hasRows: true,
        },
        2: {
          total: 30,
          employee: 0,
          employer: 0,
          hasTotal: true,
          hasRows: false,
        },
      },
      otherYears: [],
    };
    const parsePayslip = vi
      .fn<TrackerDependencies["parsePayslip"]>()
      .mockResolvedValue(parsed);
    const { app, document } = mountTracker({ parsePayslip });
    const file = new File([], "cedolino.pdf", { type: "application/pdf" });

    await app.handleFiles([file]);

    expect(app.state.months[1]).toEqual({ employee: 23.57, employer: 66.43 });
    expect(app.state.months[2]).toEqual({ employee: 30, employer: 0 });
    expect(document.getElementById("log")!.textContent).toContain(
      "ripartizione",
    );
  });

  it("copies the current state and resets the dirty status after saving", async () => {
    const onSave = vi.fn(async () => true);
    const clipboard = { writeText: vi.fn(async () => undefined) };
    const { app, document } = mountTracker({ onSave, clipboard });
    const rateInput = document.getElementById("rate") as HTMLInputElement;
    rateInput.value = "2.1";
    rateInput.dispatchEvent(
      new document.defaultView!.Event("change", { bubbles: true }),
    );

    await app.copyState();
    expect(clipboard.writeText).toHaveBeenCalledWith(
      expect.stringContaining('"rate":2.1'),
    );

    await app.save();
    expect(onSave).toHaveBeenCalledWith(app.state);
    expect(
      (document.getElementById("saveBtn") as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(document.getElementById("saveMsg")!.textContent).toContain(
      "Salvato",
    );
  });
});
