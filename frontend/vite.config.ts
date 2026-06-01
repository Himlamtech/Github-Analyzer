import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { defineConfig } from 'vite';

const defaultAllowedHosts = ['github.chipthoc.com'];

const configuredAllowedHosts = (
  process.env.VITE_ALLOWED_HOSTS ?? process.env.__VITE_ADDITIONAL_SERVER_ALLOWED_HOSTS ?? ''
)
  .split(',')
  .map((host) => host.trim())
  .filter(Boolean);

const allowedHosts = Array.from(new Set([...defaultAllowedHosts, ...configuredAllowedHosts]));

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, '.'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    allowedHosts,
    hmr: process.env.DISABLE_HMR !== 'true',
    watch: process.env.DISABLE_HMR === 'true' ? null : {},
  },
  preview: {
    host: '0.0.0.0',
    port: 3000,
  },
});
