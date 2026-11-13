/** Whether the reader dismissed the "Start here" panel, remembered in this browser only.
 *
 *  localStorage can be missing, full, or throw on access (private windows, blocked site data,
 *  sandboxed previews). Every access is wrapped: a storage failure means the panel shows again
 *  next time, never a broken page. Nothing is sent anywhere.
 */

export const START_HERE_KEY = "edm.startHere.dismissed";

type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;

function defaultStorage(): StorageLike | null {
  try {
    return typeof window !== "undefined" ? window.localStorage : null;
  } catch {
    return null;
  }
}

export function readDismissed(getStorage: () => StorageLike | null = defaultStorage): boolean {
  try {
    return getStorage()?.getItem(START_HERE_KEY) === "1";
  } catch {
    return false;
  }
}

/** Returns whether the choice was saved, so the panel can say it will show again if not. */
export function writeDismissed(dismissed: boolean, getStorage: () => StorageLike | null = defaultStorage): boolean {
  try {
    const s = getStorage();
    if (!s) return false;
    if (dismissed) s.setItem(START_HERE_KEY, "1");
    else s.removeItem(START_HERE_KEY);
    return true;
  } catch {
    return false;
  }
}

// "How to read this" on another view opens the home page with the panel showing. The flag is
// read once by the panel when it mounts.
let openRequested = false;
export function requestStartHere() { openRequested = true; }
export function takeStartHereRequest(): boolean {
  const r = openRequested;
  openRequested = false;
  return r;
}
