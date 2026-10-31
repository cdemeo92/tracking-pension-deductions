import { describe, expect, it } from "vitest";
import {
  lastNumber,
  pageLines,
  parseFile,
  parseNumber,
  type PdfJsLibrary,
  type PdfPage,
} from "../../assets/src/payslip.ts";

interface PdfLine {
  text: string;
  x?: number;
  y: number;
}

function makePdfjs(linesByPage: PdfLine[][]): PdfJsLibrary {
  return {
    getDocument: () => ({
      promise: Promise.resolve({
        numPages: linesByPage.length,
        getPage: async (pageNumber) => ({
          getTextContent: async () => ({
            items: linesByPage[pageNumber - 1].map(({ text, x = 0, y }) => ({
              str: text,
              transform: [1, 0, 0, 1, x, y],
            })),
          }),
        }),
      }),
    }),
  };
}

describe("payslip parsing", () => {
  it("parses Italian amounts and finds the last amount in a row", () => {
    expect(parseNumber("1.234,56")).toBe(1234.56);
    expect(lastNumber("imponibile 1.234,56 trattenuta 23,57")).toBe(23.57);
    expect(lastNumber("nessun importo")).toBeNull();
  });

  it("groups PDF text by row and orders each row left to right", async () => {
    const page: PdfPage = {
      getTextContent: async () => ({
        items: [
          { str: "secondo", transform: [1, 0, 0, 1, 30, 300] },
          { str: "riga sotto", transform: [1, 0, 0, 1, 0, 270] },
          { str: "primo", transform: [1, 0, 0, 1, 0, 300] },
          { str: " ", transform: [1, 0, 0, 1, 40, 300] },
        ],
      }),
    };
    await expect(pageLines(page)).resolves.toEqual([
      "primo secondo",
      "riga sotto",
    ]);
  });

  it("extracts contributions across pages and excludes transferred TFR", async () => {
    const pdfjsLib = makePdfjs([
      [
        { text: "Zucchetti", y: 300 },
        { text: "Gennaio 2026", y: 280 },
        { text: "F01998 90,00", y: 260 },
        { text: "FONTE Fondo pensione 23,57", y: 240 },
      ],
      [
        { text: "Gennaio 2026", y: 280 },
        { text: "FONTE C/Ditta Fondo pensione 66,43", y: 260 },
        { text: "FONTE T.F.R. trasferito 500,00", y: 240 },
      ],
    ]);
    const result = await parseFile(
      { arrayBuffer: async () => new ArrayBuffer(0) },
      { pdfjsLib, year: 2026 },
    );

    expect(result).toEqual({
      months: {
        1: {
          total: 90,
          employer: 66.43,
          employee: 23.57,
          hasTotal: true,
          hasRows: true,
        },
      },
      otherYears: [],
    });
  });

  it("reports years other than the active tracker year", async () => {
    const pdfjsLib = makePdfjs([[{ text: "Zucchetti Ottobre 2025", y: 300 }]]);
    const result = await parseFile(
      { arrayBuffer: async () => new ArrayBuffer(0) },
      { pdfjsLib, year: 2026 },
    );
    expect(result).toEqual({ months: {}, otherYears: ["2025"] });
  });
});
