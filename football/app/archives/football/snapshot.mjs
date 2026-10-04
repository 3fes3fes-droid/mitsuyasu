import packed from "./packed-snapshot.mjs";

let snapshot;

export function loadFootballSnapshot() {
  if (!snapshot) {
    snapshot = (async () => {
      const bytes = Uint8Array.from(atob(packed), (character) => character.charCodeAt(0));
      const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
      return new Response(stream).json();
    })().catch((error) => {
      snapshot = undefined;
      throw error;
    });
  }
  return snapshot;
}
