import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        // Dentro do Docker, VITE_PROXY_TARGET=http://backend:8000 (nome do serviço).
        // Fora do Docker (dev local), cai no padrão http://localhost:8000.
        target: process.env.VITE_PROXY_TARGET || "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
