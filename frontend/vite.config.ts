import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "./",
  build: { outDir: process.env.VITE_STATIC === "1" ? "dist-static" : "dist", emptyOutDir: false },
  server: { proxy: { "/api": "http://127.0.0.1:8000", "/reports": "http://127.0.0.1:8000" } },
});
