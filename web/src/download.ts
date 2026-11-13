/** Handing a finished file to the reader. Kept out of mapExport.ts because that module imports
 *  MapLibre (about 1 MB of script): the comparison view draws no map, and importing
 *  `downloadBlob` from mapExport made it download the whole map library just to save a PNG. */

/** Trigger a download without leaving an object URL behind. */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Revoked on the next turn so the navigation has definitely started.
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Clipboard is a SHOULD, not a MUST (§22): support is uneven and permission-gated, so the
 *  caller falls back to a download when this reports false. */
export async function copyBlobToClipboard(blob: Blob): Promise<boolean> {
  try {
    const w = window as unknown as { ClipboardItem?: new (i: Record<string, Blob>) => unknown };
    if (!navigator.clipboard || !w.ClipboardItem) return false;
    const item = new w.ClipboardItem({ "image/png": blob });
    await (navigator.clipboard as unknown as
      { write: (i: unknown[]) => Promise<void> }).write([item]);
    return true;
  } catch {
    return false;
  }
}
