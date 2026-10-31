export const MONTHS = [
  "Gennaio",
  "Febbraio",
  "Marzo",
  "Aprile",
  "Maggio",
  "Giugno",
  "Luglio",
  "Agosto",
  "Settembre",
  "Ottobre",
  "Novembre",
  "Dicembre",
] as const;

export interface PdfTextItem {
  str: string;
  transform: number[];
}

export interface PdfPage {
  getTextContent(): Promise<{ items: PdfTextItem[] }>;
}

export interface PdfDocument {
  numPages: number;
  getPage(pageNumber: number): Promise<PdfPage>;
}

export interface PdfJsLibrary {
  getDocument(options: { data: ArrayBuffer }): { promise: Promise<PdfDocument> };
}

export interface ParsedMonth {
  total: number;
  employer: number;
  employee: number;
  hasTotal: boolean;
  hasRows: boolean;
}

export interface ParsedPayslip {
  months: Record<number, ParsedMonth>;
  otherYears: string[];
}

export interface ParsePayslipOptions {
  pdfjsLib: PdfJsLibrary;
  year: number;
  months?: readonly string[];
}

const NUMBER = /\d{1,3}(?:\.\d{3})*,\d{2}(?!\d)/g;

export function parseNumber(value: string): number {
  return Number.parseFloat(value.replace(/\./g, "").replace(",", "."));
}

export function lastNumber(line: string): number | null {
  const matches = line.match(NUMBER);
  return matches ? parseNumber(matches[matches.length - 1]) : null;
}

export async function pageLines(page: PdfPage): Promise<string[]> {
  const content = await page.getTextContent();
  const rows = new Map<number, Array<[number, string]>>();

  for (const item of content.items) {
    if (!item.str.trim()) continue;
    const y = Math.round(item.transform[5] / 3);
    const row = rows.get(y) ?? [];
    row.push([item.transform[4], item.str]);
    rows.set(y, row);
  }

  return [...rows.entries()]
    .sort(([firstY], [secondY]) => secondY - firstY)
    .map(([, row]) =>
      row
        .sort(([firstX], [secondX]) => firstX - secondX)
        .map((part) => part[1])
        .join(" "),
    );
}

export async function parseFile(
  file: Pick<File, "arrayBuffer">,
  { pdfjsLib, year, months = MONTHS }: ParsePayslipOptions,
): Promise<ParsedPayslip> {
  const pdf = await pdfjsLib.getDocument({ data: await file.arrayBuffer() }).promise;
  const parsedMonths: ParsedPayslip["months"] = {};
  const otherYears = new Set<string>();
  const periodPattern = new RegExp(`(${months.join("|")})\\s+(20\\d\\d)`, "i");

  for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
    const lines = await pageLines(await pdf.getPage(pageNumber));
    const period = lines.join("\n").match(periodPattern);
    if (!period) continue;

    const month =
      months.findIndex((name) => name.toLowerCase() === period[1].toLowerCase()) + 1;
    if (Number(period[2]) !== year) {
      otherYears.add(period[2]);
      continue;
    }

    const monthData = parsedMonths[month] ?? {
      total: 0,
      employer: 0,
      employee: 0,
      hasTotal: false,
      hasRows: false,
    };

    for (const line of lines) {
      if (/F01998|prev\.?\s*compl.*deduc/i.test(line)) {
        const amount = lastNumber(line);
        if (amount !== null) {
          monthData.total += amount;
          monthData.hasTotal = true;
        }
      } else if (/FONTE/i.test(line) && !/T\.F\.R\.\s*trasferito/i.test(line)) {
        const amount = lastNumber(line);
        if (amount === null) continue;
        monthData.hasRows = true;
        if (/C\/Ditta/i.test(line)) monthData.employer += amount;
        else monthData.employee += amount;
      }
    }

    parsedMonths[month] = monthData;
  }

  return { months: parsedMonths, otherYears: [...otherYears] };
}