import { injectState } from "./artifact.ts";
import { parseFile, type PdfJsLibrary } from "./payslip.ts";
import { createTracker } from "./tracker.ts";
import type { TrackerState } from "./calculations.ts";

interface ArtifactPublisher {
  publish(html: string): Promise<void>;
}

declare global {
  interface Window {
    pdfjsLib?: PdfJsLibrary;
    claude?: {
      use(name: "artifact"): Promise<ArtifactPublisher | undefined>;
    };
  }
}

const sourceHtml = `<!DOCTYPE html>\n${document.documentElement.outerHTML}`;
const stateElement = document.getElementById("state");
let initialState: Partial<TrackerState> = {};

if (stateElement) {
  try {
    initialState = JSON.parse(stateElement.textContent ?? "") as Partial<TrackerState>;
  } catch {
    initialState = {};
  }
}

createTracker({
  document,
  initialState,
  parsePayslip: (file, options) => {
    const pdfjsLib = window.pdfjsLib;
    if (!pdfjsLib) throw new Error("PDF.js is unavailable");
    return parseFile(file, { ...options, pdfjsLib });
  },
  clipboard: navigator.clipboard,
  onSave: async (state) => {
    const artifact = window.claude
      ? await window.claude.use("artifact")
      : undefined;
    if (!artifact) return false;
    await artifact.publish(injectState(sourceHtml, state));
    return true;
  },
});