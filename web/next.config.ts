import type { NextConfig } from "next";

// GitHub Pages serves the site from /<repo>/, so the deploy workflow sets
// NEXT_PUBLIC_BASE_PATH; locally it stays empty.
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  basePath,
  images: { unoptimized: true },
  // cacheComponents / partialPrefetching are omitted: Next.js refuses PPR in export mode.
};

export default nextConfig;
