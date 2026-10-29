/**
 * Municipality outlines to SVG paths, at build time.
 *
 * An equirectangular projection with longitude scaled by cos(mid-latitude) is
 * indistinguishable from a proper projection at county scale (Varaždin County
 * spans about 0.4° of latitude) and needs no library.
 */
import type { Boundaries } from "@/lib/contract";

type Ring = [number, number][];
type MultiPolygon = Ring[][];

export type Shape = {
  slug: string;
  name: string;
  hasData: boolean;
  /** SVG path data in the map's coordinate space. */
  d: string;
  /** Where to put the name: a point inside the municipality. */
  labelX: number;
  labelY: number;
};

export type ProjectedMap = { width: number; height: number; shapes: Shape[] };

export function projectBoundaries(
  boundaries: Boundaries,
  width = 800,
  padding = 8,
): ProjectedMap {
  const polygons = boundaries.features.map(
    (f) => (f.geometry as { coordinates: MultiPolygon }).coordinates,
  );
  // features -> polygons -> rings -> points. Loops, not Math.min(...all): spreading
  // ~150k vertices (all of Croatia) exceeds the engine's argument limit.
  let [minLon, maxLon, minLat, maxLat] = [
    Infinity,
    -Infinity,
    Infinity,
    -Infinity,
  ];
  for (const [lon, lat] of polygons.flat(3) as [number, number][]) {
    if (lon < minLon) minLon = lon;
    if (lon > maxLon) maxLon = lon;
    if (lat < minLat) minLat = lat;
    if (lat > maxLat) maxLat = lat;
  }
  const kx = Math.cos((((minLat + maxLat) / 2) * Math.PI) / 180);

  const spanX = (maxLon - minLon) * kx;
  const spanY = maxLat - minLat;
  const scale = (width - 2 * padding) / spanX;
  const height = Math.round(spanY * scale + 2 * padding);

  const x = (lon: number) => padding + (lon - minLon) * kx * scale;
  const y = (lat: number) => padding + (maxLat - lat) * scale;
  // Small maps round to whole units: finer detail is invisible there and only adds bytes.
  const decimals = width >= 600 ? 1 : 0;
  const fmt = (n: number) => n.toFixed(decimals);

  const shapes = boundaries.features.map((feature, i) => {
    const rings = polygons[i].flat();
    const d = rings
      .map((ring) => {
        const points = ring.map(
          ([lon, lat]) => `${fmt(x(lon))},${fmt(y(lat))}`,
        );
        // Neighbouring vertices that round to the same point add nothing.
        const unique = points.filter((p, j) => j === 0 || p !== points[j - 1]);
        return `M${unique.join("L")}Z`;
      })
      .join("");
    return {
      slug: feature.properties.slug,
      name: feature.properties.name,
      hasData: feature.properties.hasData,
      d,
      labelX: x(feature.properties.labelLon),
      labelY: y(feature.properties.labelLat),
    };
  });
  return { width, height, shapes };
}
