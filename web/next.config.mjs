/** @type {import('next').NextConfig} */
const nextConfig = {
  // Proxy /api calls to FastAPI backend (localhost:8000)
  // This helps avoid Mixed Content issues during local development and self-hosting
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://localhost:8000/api/v1/:path*',
      },
    ]
  },
};

export default nextConfig;
