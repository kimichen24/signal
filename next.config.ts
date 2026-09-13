import type { NextConfig } from "next";

const isGitHubPages = process.env.DEPLOY_TARGET === "github-pages";

const nextConfig: NextConfig = isGitHubPages
  ? {
      output: "export",
      basePath: "/signal",
      trailingSlash: true,
      images: { unoptimized: true },
    }
  : {};

export default nextConfig;
