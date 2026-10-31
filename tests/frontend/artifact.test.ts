import { describe, expect, it } from "vitest";
import { injectState } from "../../assets/src/artifact.ts";

describe("injectState", () => {
  it("replaces only the tracker state and escapes script openers", () => {
    const source =
      '<html><script type="application/json" id="state">{}</script><p>unchanged</p></html>';
    const state = { year: 2026, note: "</script><script>" };

    const result = injectState(source, state);

    expect(result).toContain(
      '{"year":2026,"note":"\\u003c/script>\\u003cscript>"}',
    );
    expect(result).toContain("<p>unchanged</p>");
    expect(result.match(/id="state"/g)).toHaveLength(1);
  });
});
