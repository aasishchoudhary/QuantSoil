import {defineConfig} from "vite";
import cesium from "vite-plugin-cesium";

const analystProxyTarget = process.env.ANALYST_PROXY_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [cesium()],
  server: {
    proxy: {
      "/v1": {
        target: analystProxyTarget,
        changeOrigin: true,
      },
    },
  },
});
