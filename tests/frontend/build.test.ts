import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const builtHtmlPath = resolve(process.cwd(), "dist/template.html");

describe("single-file Vite build", () => {
  it("inlines application code and keeps only the approved PDF.js CDN scripts external", () => {
    const html = readFileSync(builtHtmlPath, "utf8");
    const externalScripts = [
      ...html.matchAll(/<script\b[^>]*\bsrc=["']([^"']+)["'][^>]*>/gi),
    ].map((match) => match[1]);
    const inlineModule = [
      ...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi),
    ].find((match) => /type=["']module["']/i.test(match[1]));

    expect(html).toContain('<script type="application/json" id="state">');
    expect(html).toContain("Salva");
    expect(externalScripts).toHaveLength(2);
    expect(
      externalScripts.every((src) =>
        src.startsWith("https://cdnjs.cloudflare.com/ajax/libs/pdf.js/"),
      ),
    ).toBe(true);
    expect(inlineModule).toBeDefined();
    expect(inlineModule![2]).not.toMatch(/\n\s{2,}/);
    expect(html).not.toContain("/src/main.js");
  });
});
