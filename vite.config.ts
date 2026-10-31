import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

const assetsRoot = fileURLToPath(new URL("./assets/", import.meta.url));

export default defineConfig({
  root: assetsRoot,
  plugins: [viteSingleFile()],
  build: {
    outDir: fileURLToPath(new URL("./dist/", import.meta.url)),
    emptyOutDir: true,
    rollupOptions: {
      input: fileURLToPath(new URL("./assets/template.html", import.meta.url)),
    },
  },
});