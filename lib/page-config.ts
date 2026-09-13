/**
 * Shared page config for dual deployment targets.
 * Import and re-export in each page:
 *   export { dynamic } from "@/lib/page-config";
 */
export const dynamic =
  process.env.DEPLOY_TARGET === "github-pages" ? "force-static" : "force-dynamic";
