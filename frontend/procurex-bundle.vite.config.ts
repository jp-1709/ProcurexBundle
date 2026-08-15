// Build config used by procurex_bundle to compile the ProcureX frontend
// (https://github.com/QuantbitERP/ProcureX) into a static SPA that Frappe serves itself.
//
// It is copied into the cloned frontend at build time and passed to
// `vite build --config`, so the frontend repository is never modified:
//   - `vite.base`  -> assets are emitted for /assets/procurex_bundle/procurex/
//   - router basepath -> the app lives under the /procurex route of the Frappe site
//   - `spa.enabled` -> prerenders a static shell (dist/client/_shell.html), no Node server
//   - `nitro: false` -> plain vite output, nothing to run in production
import { defineConfig } from "@lovable.dev/vite-tanstack-config";

const BASE = process.env.PROCUREX_ASSET_BASE ?? "/assets/procurex_bundle/procurex/";
const BASEPATH = process.env.PROCUREX_BASEPATH ?? "/procurex";

const routerBasepath = {
  name: "procurex-bundle:router-basepath",
  enforce: "pre" as const,
  transform(code: string, id: string) {
    if (!id.replace(/\\/g, "/").endsWith("/src/router.tsx")) return null;
    if (!code.includes("createRouter({")) return null;
    return code.replace("createRouter({", `createRouter({ basepath: ${JSON.stringify(BASEPATH)},`);
  },
};

export default defineConfig({
  plugins: [routerBasepath],
  tanstackStart: {
    server: { entry: "server" },
    spa: { enabled: true },
  },
  nitro: false,
  vite: {
    base: BASE,
  },
});
