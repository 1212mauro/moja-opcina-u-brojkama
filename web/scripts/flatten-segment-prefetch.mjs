/**
 * Post-build fix for static hosting (GitHub Pages).
 *
 * Next 16's static export writes segment-prefetch payloads as nested files,
 * e.g. `metodologija/__next.metodologija/__PAGE__.txt`, but the client router
 * requests the dotted flat name `metodologija/__next.metodologija.__PAGE__.txt`.
 * A server can rewrite one to the other; a plain static host cannot, so every
 * prefetch of such a route 404s (navigation still works, by full page load).
 * This copies each nested payload to the flat name the router asks for.
 * Seen with Next 16.4; if an upgrade changes the layout, the build fails here.
 */
import { copyFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";

const out = path.resolve(process.argv[2] ?? "out");
let copied = 0;

function filesUnder(dir) {
  return readdirSync(dir).flatMap((name) => {
    const full = path.join(dir, name);
    return statSync(full).isDirectory() ? filesUnder(full) : [full];
  });
}

function walk(dir) {
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name);
    // _next/ holds static assets only, never segment payloads.
    if (name === "_next" || !statSync(full).isDirectory()) continue;
    if (name.startsWith("__next.")) {
      for (const file of filesUnder(full)) {
        const parts = path.relative(full, file).split(path.sep);
        copyFileSync(file, path.join(dir, [name, ...parts].join(".")));
        copied += 1;
      }
    } else {
      walk(full);
    }
  }
}

walk(out);
if (copied === 0) {
  console.error(
    "flatten-segment-prefetch: no __next.* segment folders found; has Next changed the export layout?",
  );
  process.exit(1);
}
console.log(
  `flatten-segment-prefetch: ${copied} payloads copied to flat names`,
);
