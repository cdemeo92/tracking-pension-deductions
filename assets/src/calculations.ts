export interface MonthlyContributions {
  employee: number;
  employer: number;
}

export interface VoluntaryPayment {
  date: string;
  amount: number;
}

export interface TrackerState {
  version?: number;
  year: number;
  limit: number;
  rate: number;
  base: number;
  bonus13: number;
  bonus14: number;
  months: Record<string, MonthlyContributions>;
  voluntary: VoluntaryPayment[];
}

export interface CalculationSummary {
  employee: number;
  employer: number;
  voluntary: number;
  total: number;
  remaining: number;
  estimateTotal: number;
  remainingAtYearEnd: number;
  estimates: Record<number, number>;
  lastMonth: number;
}

export function round2(value: number): number {
  return Math.round(value * 100) / 100;
}

export function compute(state: TrackerState): CalculationSummary {
  let employee = 0;
  let employer = 0;
  let lastMonth = 0;

  for (const [month, values] of Object.entries(state.months)) {
    employee += values.employee;
    employer += values.employer;
    lastMonth = Math.max(lastMonth, Number(month));
  }

  const voluntary = state.voluntary.reduce(
    (total, payment) => total + payment.amount,
    0,
  );
  const estimates: Record<number, number> = {};
  let estimateTotal = 0;

  if (lastMonth > 0 && state.rate > 0 && state.base > 0) {
    for (let month = lastMonth + 1; month <= 12; month += 1) {
      const bonus = month === 6 ? state.bonus14 : month === 12 ? state.bonus13 : 0;
      estimates[month] = round2(((state.base + bonus) * state.rate) / 100);
      estimateTotal += estimates[month];
    }
  }

  const total = employee + employer + voluntary;
  const remaining = state.limit - total;

  return {
    employee,
    employer,
    voluntary,
    total,
    remaining,
    estimateTotal,
    remainingAtYearEnd: remaining - estimateTotal,
    estimates,
    lastMonth,
  };
}