const STATE_BLOCK = /(<script type="application\/json" id="state">)(.*?)(<\/script>)/s;

export function injectState(sourceHtml: string, state: unknown): string {
  if (!STATE_BLOCK.test(sourceHtml)) {
    throw new Error("Tracker state block not found in HTML");
  }

  const serializedState = JSON.stringify(state);
  if (serializedState === undefined) {
    throw new Error("Tracker state cannot be serialized as JSON");
  }

  const safeState = serializedState.replace(/</g, "\\u003c");
  return sourceHtml.replace(
    STATE_BLOCK,
    (_match, openingTag: string, _previousState: string, closingTag: string) =>
      `${openingTag}${safeState}${closingTag}`,
  );
}