/**
 * Build-time access to the JSON the pipeline exports (`opcina export`).
 *
 * Real data lives in `public/data/` (git-ignored; produced by the nightly job).
 * When it is absent, as in CI, the site builds from the small committed fixture in
 * `fixtures/data/`, so the build never depends on a data run. `DATA_DIR` overrides both.
 */
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

import type {
  MunicipalityPage,
  SearchIndex,
  SourceStatus,
} from "@/lib/contract";

function dataDir(): string {
  if (process.env.DATA_DIR) return path.resolve(process.env.DATA_DIR);
  const real = path.join(process.cwd(), "public", "data");
  if (existsSync(path.join(real, "search-index.json"))) return real;
  return path.join(process.cwd(), "fixtures", "data");
}

function readJson<T>(...parts: string[]): T {
  return JSON.parse(readFileSync(path.join(dataDir(), ...parts), "utf-8")) as T;
}

export function loadSearchIndex(): SearchIndex {
  return readJson<SearchIndex>("search-index.json");
}

export function loadPage(slug: string): MunicipalityPage {
  return readJson<MunicipalityPage>("m", `${slug}.json`);
}

export function loadSourceStatus(): SourceStatus {
  return readJson<SourceStatus>("sources.json");
}

/** Slugs of every municipality that has a page. */
export function pageSlugs(): string[] {
  return loadSearchIndex().entries.map((entry) => entry.slug);
}
