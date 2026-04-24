/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  images: { unoptimized: true },
  trailingSlash: true,
  async rewrites() {
    if (process.env.NODE_ENV !== 'development') return [];
    return [
      { source: '/api/stream/:path*', destination: 'http://localhost:8000/api/stream/:path*' },
      { source: '/api/:path*',        destination: 'http://localhost:8000/api/:path*' },
    ];
  },
};

export default nextConfig;
