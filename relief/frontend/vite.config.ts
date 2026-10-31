import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the app runs on :5173 and forwards /api to the FastAPI server on :8000.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": { target: process.env.RELIEF_API_URL ?? "http://127.0.0.1:8000", changeOrigin: true } } },
  build: { outDir: "dist", sourcemap: false },
});
