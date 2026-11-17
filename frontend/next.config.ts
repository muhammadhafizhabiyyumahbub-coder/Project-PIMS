import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  async rewrites() {
    // Dev proxy: keep browser same-origin so no CORS setup is needed on the API.
    const api = process.env.PIMS_API_URL ?? "http://localhost:8000";
    return [
      { source: "/api/v1/:path*", destination: `${api}/api/v1/:path*` },
      { source: "/health", destination: `${api}/health` },
      { source: "/health/:path*", destination: `${api}/health/:path*` },
    ];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
