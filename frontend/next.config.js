/** @type {import('next').NextConfig} */
const nextConfig = {
    output: "standalone",
    images: {
        remotePatterns: [
            { protocol: "https", hostname: "avatars.githubusercontent.com" },
            { protocol: "https", hostname: "github.com" },
        ],
    },
    // Proxy API calls through Next.js server so the browser never needs to
    // resolve the internal Docker hostname 'api'. Both SSR and client-side
    // fetches use relative paths (/dashboard/*) which are rewritten here.
    async rewrites() {
        const apiBase = process.env.API_INTERNAL_URL ?? "http://api:8000";
        return [
            { source: "/dashboard/:path*", destination: `${apiBase}/dashboard/:path*` },
            { source: "/health", destination: `${apiBase}/health` },
            { source: "/metrics", destination: `${apiBase}/metrics` },
        ];
    },
};

module.exports = nextConfig;
