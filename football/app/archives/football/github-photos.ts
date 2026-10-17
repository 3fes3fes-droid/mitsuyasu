import ranges from "./photo-ranges.json";

const archive = new URL("../Football_archive_single.html", document.baseURI).href;
const cache = new Map<string, Promise<string>>();
const pending: Array<() => void> = [];
let active = 0;

async function image(path: string): Promise<string> {
  if (active >= 6) await new Promise<void>(resolve => pending.push(resolve));
  else active++;
  try {
    const [offset, length, type] = ranges[path as keyof typeof ranges];
    const end = Number(offset) + Number(length) - 1;
    const response = await fetch(archive, {
      headers: { Range: `bytes=${offset}-${end}` },
      signal: AbortSignal.timeout(20000),
    });
    if (response.status !== 206 || response.headers.get("Content-Range") !== `bytes ${offset}-${end}/88834538`) {
      throw new Error("Photo range unavailable");
    }
    const encoded = await response.text();
    if (encoded.length !== Number(length)) throw new Error("Incomplete photo");
    const bytes = Uint8Array.from(atob(encoded), character => character.charCodeAt(0));
    return URL.createObjectURL(new Blob([bytes], { type: String(type) }));
  } finally {
    const next = pending.shift();
    if (next) next();
    else active--;
  }
}

export function githubPhoto(path: string): Promise<string> {
  const clean = path.replace(/^\//, "");
  if (!(clean in ranges)) {
    return Promise.resolve(clean.startsWith("football/players/") ? `./${clean.slice("football/".length)}` : path);
  }
  if (!cache.has(clean)) {
    const request = image(clean).catch(error => { cache.delete(clean); throw error; });
    cache.set(clean, request);
  }
  return cache.get(clean)!;
}
