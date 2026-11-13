/** The export images' shared text palette: one definition, so a country, Gulf, Compare and world
 *  image cannot drift apart in ink or face. Band opacity and panel colours stay with each frame. */
export const INK = "#d4dfea";
export const DIM = "#93a5b3";
export const SANS = '"Inter", system-ui, sans-serif';

/** Draw one line of text into an export image, shrinking the font until it fits `maxWidth`.
 *
 *  Iteration 20. The export frames were laid out against the fonts on the machine that built them;
 *  on a Linux runner the fallback sans is wider and the longest lines ran off the 1600-pixel image
 *  (the CI browser job). A line is never cut or wrapped: the words an image carries about what it is
 *  not are the reason it can travel without the page, so the text shrinks instead. The font is
 *  restored afterwards so the next line starts at its designed size. */
export function fillFitted(c: CanvasRenderingContext2D, text: string, x: number, y: number, maxWidth: number): void {
  const font = c.font;
  const m = /(\d+(?:\.\d+)?)px/.exec(font);
  let px = m ? Number(m[1]) : 16;
  while (px > 6 && c.measureText(text).width > maxWidth) {
    px -= 0.5;
    c.font = font.replace(/\d+(?:\.\d+)?px/, `${px}px`);
  }
  c.fillText(text, x, y);
  c.font = font;
}
