import { compute, round2, type CalculationSummary, type TrackerState } from "./calculations.ts";
import { MONTHS, type ParsedPayslip } from "./payslip.ts";

const PARAMS = ["year", "limit", "rate", "base", "bonus14", "bonus13"] as const;
const DEFAULT_STATE: TrackerState = {
  version: 1,
  year: 2026,
  limit: 5300,
  rate: 0,
  base: 0,
  bonus13: 0,
  bonus14: 0,
  months: {},
  voluntary: [],
};

type TrackerParameter = (typeof PARAMS)[number];
type LogEntry = { text: string; error?: boolean };
type PayslipParser = (
  file: File,
  options: { year: number; months: readonly string[] },
) => Promise<ParsedPayslip>;

export interface TrackerDependencies {
  document: Document;
  initialState?: Partial<TrackerState>;
  parsePayslip: PayslipParser;
  clipboard?: Pick<Clipboard, "writeText">;
  onSave?: (state: TrackerState) => Promise<boolean | void>;
}

export interface TrackerController {
  state: TrackerState;
  compute(): CalculationSummary;
  render(): void;
  handleFiles(files: readonly File[]): Promise<void>;
  save(): Promise<void>;
  copyState(): Promise<void>;
}

const euro = (value: number): string =>
  Number(value).toLocaleString("it-IT", {
    style: "currency",
    currency: "EUR",
  });

function escapeHtml(value: string | number): string {
  const entities: Record<string, string> = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  };
  return String(value).replace(/[&<>"']/g, (character) => entities[character]);
}

export function createTracker({
  document,
  initialState = {},
  parsePayslip,
  clipboard,
  onSave,
}: TrackerDependencies): TrackerController {
  const state: TrackerState = {
    ...DEFAULT_STATE,
    ...initialState,
    months: { ...(initialState.months ?? {}) },
    voluntary: (initialState.voluntary ?? []).map((payment) => ({ ...payment })),
  };
  let dirty = false;

  function getElement<T extends HTMLElement = HTMLElement>(id: string): T {
    const element = document.getElementById(id);
    if (!element) throw new Error(`Tracker element #${id} not found`);
    return element as T;
  }

  function showLog(items: LogEntry[]): void {
    const list = getElement<HTMLUListElement>("log");
    list.replaceChildren();
    for (const item of items) {
      const entry = document.createElement("li");
      if (item.error) entry.classList.add("error");
      entry.textContent = item.text;
      list.append(entry);
    }
  }

  function render(): void {
    const totals = compute(state);
    const kpi = (label: string, amount: number, className = ""): string =>
      `<div class="kpi ${className}"><span>${label}</span><b>${euro(amount)}</b></div>`;

    getElement("kpis").innerHTML = [
      kpi("Versamenti volontari", totals.voluntary),
      kpi("Da busta paga: tuo", totals.employee),
      kpi("Da busta paga: datore", totals.employer),
      kpi("Totale già deducibile", totals.total),
      totals.remaining >= 0
        ? kpi("Ti manca oggi", totals.remaining, "main")
        : kpi("Eccedenza oggi", -totals.remaining, "over"),
      kpi("Stima in busta fino a dicembre", totals.estimateTotal),
      totals.remainingAtYearEnd >= 0
        ? kpi("Stima mancante a fine anno", totals.remainingAtYearEnd, "main")
        : kpi("Stima eccedenza a fine anno", -totals.remainingAtYearEnd, "over"),
    ].join("");

    getElement("hint").hidden = !(
      totals.lastMonth > 0 && !(state.rate > 0 && state.base > 0)
    );

    const percent = (value: number): number =>
      Math.max(0, Math.min(100, state.limit > 0 ? (value / state.limit) * 100 : 0));
    const segments: Array<[number, string, string]> = [
      [totals.voluntary, "var(--acc)", "Volontari"],
      [totals.employee, "#5aa88d", "Tuo (busta)"],
      [totals.employer, "#9fcfbc", "Datore"],
      [
        totals.estimateTotal,
        "repeating-linear-gradient(45deg,var(--line),var(--line) 4px,var(--card) 4px,var(--card) 8px)",
        "Stima busta",
      ],
    ];
    getElement("bar").innerHTML = segments
      .map(
        ([value, color]) =>
          `<i style="width:${percent(value)}%;background:${color}"></i>`,
      )
      .join("");
    getElement("legend").innerHTML =
      segments
        .map(
          ([, color, label]) =>
            `<span><em style="background:${color}"></em>${label}</span>`,
        )
        .join("") + `<span>Limite ${euro(state.limit)}</span>`;

    const months = Object.keys(state.months)
      .map(Number)
      .sort((first, second) => first - second);
    let rows =
      "<thead><tr><th>Mese</th><th>Tuo</th><th>Datore</th><th>Totale</th><th></th></tr></thead><tbody>";
    if (!months.length) {
      rows +=
        '<tr><td colspan="5" style="text-align:left;color:var(--mut)">Nessuna busta paga. Carica i PDF o aggiungi un mese a mano.</td></tr>';
    }
    for (const month of months) {
      const values = state.months[month];
      const name = MONTHS[month - 1];
      if (!values || !name) continue;
      rows += `<tr><td>${name}</td><td><input type="number" step="0.01" value="${escapeHtml(values.employee)}" data-month="${month}" data-field="employee" aria-label="Tuo ${name}"></td><td><input type="number" step="0.01" value="${escapeHtml(values.employer)}" data-month="${month}" data-field="employer" aria-label="Datore ${name}"></td><td>${euro(round2(values.employee + values.employer))}</td><td><button class="icon" data-delete-month="${month}" aria-label="Elimina ${name}">✕</button></td></tr>`;
    }
    for (const [month, amount] of Object.entries(totals.estimates)) {
      const name = MONTHS[Number(month) - 1];
      if (name) {
        rows += `<tr class="estimate"><td>${name} (stima)</td><td></td><td></td><td>${euro(amount)}</td><td></td></tr>`;
      }
    }
    rows += `</tbody><tfoot><tr><td>Totale</td><td>${euro(totals.employee)}</td><td>${euro(totals.employer)}</td><td>${euro(totals.employee + totals.employer)}</td><td></td></tr></tfoot>`;
    getElement("monthsTable").innerHTML = rows;

    getElement<HTMLSelectElement>("newMonth").innerHTML = MONTHS.map(
      (name, index) =>
        state.months[String(index + 1)]
          ? ""
          : `<option value="${index + 1}">${name}</option>`,
    ).join("");
    getElement("voluntary").innerHTML = state.voluntary
      .map(
        (payment, index) =>
          `<div class="row"><div><label>Data (facoltativa)</label><input type="text" value="${escapeHtml(payment.date)}" data-vol="${index}" data-field="date" placeholder="gg/mm/aaaa"></div><div><label>Importo (€)</label><input type="number" step="0.01" value="${escapeHtml(payment.amount)}" data-vol="${index}" data-field="amount"></div><button class="icon" data-delete-vol="${index}" aria-label="Elimina versamento">✕</button></div>`,
      )
      .join("");

    for (const id of PARAMS) {
      if (document.activeElement?.id !== id) {
        getElement<HTMLInputElement>(id).value = String(state[id]);
      }
    }
    getElement<HTMLButtonElement>("saveBtn").disabled = !dirty;
    if (dirty) getElement("saveMsg").textContent = "Hai modifiche non salvate.";
  }

  function touch(): void {
    dirty = true;
    render();
  }

  async function copyState(): Promise<void> {
    try {
      if (!clipboard?.writeText) throw new Error("Clipboard unavailable");
      await clipboard.writeText(JSON.stringify(state));
      getElement("saveMsg").textContent = "Dati copiati.";
    } catch {
      getElement("saveMsg").textContent =
        "Copia non riuscita. Copia il testo a mano.";
      document.defaultView?.prompt("Dati", JSON.stringify(state));
    }
  }

  async function save(): Promise<void> {
    try {
      if (!onSave) {
        getElement("saveMsg").textContent =
          'Qui non posso salvare. Usa "Copia dati" e incollali nella chat con la skill.';
        return;
      }
      const saved = await onSave(state);
      if (saved === false) {
        getElement("saveMsg").textContent =
          'Qui non posso salvare. Usa "Copia dati" e incollali nella chat con la skill.';
        return;
      }
      dirty = false;
      render();
      getElement("saveMsg").textContent = "Salvato.";
    } catch (error: unknown) {
      const code =
        typeof error === "object" && error !== null && "code" in error
          ? error.code
          : undefined;
      getElement("saveMsg").textContent =
        code === "not_granted" || code === "not_writer"
          ? "Questa pagina è in sola lettura: puoi provare i calcoli ma non salvare."
          : code === "conflict"
            ? "La pagina è stata aggiornata altrove: ricarica e ripeti la modifica."
            : 'Salvataggio non riuscito. Usa "Copia dati" e incollali nella chat con la skill.';
    }
  }

  async function handleFiles(files: readonly File[]): Promise<void> {
    showLog([{ text: "Leggo i file…" }]);
    const messages: LogEntry[] = [];
    let savedCount = 0;

    for (const file of files) {
      try {
        const result = await parsePayslip(file, {
          year: state.year,
          months: MONTHS,
        });
        if (result.otherYears.length) {
          messages.push({
            error: true,
            text: `${file.name}: buste di un anno diverso (${result.otherYears.join(", ")}) ignorate. La pagina è impostata sul ${state.year}.`,
          });
        }

        const months = Object.keys(result.months);
        if (!months.length && !result.otherYears.length) {
          messages.push({
            error: true,
            text: `${file.name}: nessuna busta paga riconosciuta. Inserisci i valori a mano.`,
          });
        }

        for (const month of months) {
          const monthNumber = Number(month);
          const values = result.months[monthNumber];
          const name = MONTHS[monthNumber - 1];
          if (!values || !name) continue;
          if (!values.hasTotal) {
            messages.push({
              error: true,
              text: `${name} (${file.name}): voce dei contributi deducibili non trovata. Non salvato: inserisci i valori a mano.`,
            });
            continue;
          }
          if (
            values.hasRows &&
            Math.abs(values.employee + values.employer - values.total) > 0.02
          ) {
            messages.push({
              error: true,
              text: `${name} (${file.name}): tuo + datore (${euro(round2(values.employee + values.employer))}) non coincide con il totale (${euro(round2(values.total))}). Non salvato: controlla e inserisci a mano.`,
            });
            continue;
          }

          const employer = round2(values.employer);
          state.months[month] = {
            employee: round2(values.total - employer),
            employer,
          };
          savedCount += 1;
          messages.push(
            values.hasRows
              ? { text: `${name}: letto, totale ${euro(round2(values.total))}.` }
              : {
                  error: true,
                  text: `${name}: letto il totale ${euro(round2(values.total))} ma non la ripartizione tra te e il datore. Ho messo tutto in "Tuo": correggi a mano.`,
                },
          );
        }
      } catch {
        messages.push({
          error: true,
          text: `${file.name}: file non leggibile. Inserisci i valori a mano.`,
        });
      }
    }

    showLog(messages);
    if (savedCount) touch();
    else render();
  }

  document.addEventListener("change", (event: Event) => {
    const target = event.target;
    if (!(target instanceof HTMLInputElement || target instanceof HTMLSelectElement)) return;

    const month = target.dataset.month;
    if (month) {
      const field = target.dataset.field;
      const contribution = state.months[month];
      if (!contribution) return;
      if (field === "employee" || field === "employer") {
        contribution[field] = Number(target.value) || 0;
        touch();
      }
      return;
    }

    const voluntaryIndex = target.dataset.vol;
    if (voluntaryIndex !== undefined) {
      const payment = state.voluntary[Number(voluntaryIndex)];
      const field = target.dataset.field;
      if (!payment) return;
      if (field === "amount") payment.amount = Number(target.value) || 0;
      else if (field === "date") payment.date = target.value;
      else return;
      touch();
      return;
    }

    if (PARAMS.includes(target.id as TrackerParameter)) {
      const parameter = target.id as TrackerParameter;
      state[parameter] = Number(target.value) || 0;
      touch();
    }
  });

  document.addEventListener("click", (event: MouseEvent) => {
    if (!(event.target instanceof Element)) return;
    const button = event.target.closest("button");
    if (!button) return;
    const monthToDelete = button.dataset.deleteMonth;
    if (monthToDelete) {
      delete state.months[monthToDelete];
      touch();
    }
    const voluntaryToDelete = button.dataset.deleteVol;
    if (voluntaryToDelete !== undefined) {
      state.voluntary.splice(Number(voluntaryToDelete), 1);
      touch();
    }
    if (button.id === "addVoluntary") {
      state.voluntary.push({ date: "", amount: 0 });
      touch();
    }
    if (button.id === "addMonth") {
      const month = getElement<HTMLSelectElement>("newMonth").value;
      if (month) {
        state.months[month] = { employee: 0, employer: 0 };
        touch();
      }
    }
    if (button.id === "saveBtn") void save();
    if (button.id === "copyBtn") void copyState();
  });

  const drop = getElement<HTMLDivElement>("drop");
  const fileInput = getElement<HTMLInputElement>("fileInput");
  drop.onclick = () => fileInput.click();
  drop.onkeydown = (event: KeyboardEvent) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      fileInput.click();
    }
  };
  fileInput.onchange = () => {
    void handleFiles(Array.from(fileInput.files ?? []));
    fileInput.value = "";
  };
  drop.ondragover = (event: DragEvent) => {
    event.preventDefault();
    drop.classList.add("active");
  };
  drop.ondragleave = () => drop.classList.remove("active");
  drop.ondrop = (event: DragEvent) => {
    event.preventDefault();
    drop.classList.remove("active");
    const files = Array.from(event.dataTransfer?.files ?? []).filter((file) =>
      /pdf$/i.test(file.name),
    );
    void handleFiles(files);
  };

  render();
  return { state, compute: () => compute(state), render, handleFiles, save, copyState };
}