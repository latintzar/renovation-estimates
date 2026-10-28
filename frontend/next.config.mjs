/** @type {import('next').NextConfig} */
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

const nextConfig = {
  // A constrained local verification host can avoid generated Webpack disk cache.
  webpack(config) {
    if (process.env.ESTIMATES_BUILD_CACHE === '0') config.cache = false;
    return config;
  },
  images: {
    // Allow any external images - universal scraper can fetch from any domain
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
      {
        protocol: 'http',
        hostname: '**',
      },
    ],
  },
  // Proxy API requests to the backend
  async rewrites() {
    return [
      {
        source: '/api/health',
        destination: `${BACKEND_URL}/health`,
      },
      {
        source: '/api/listings',
        destination: `${BACKEND_URL}/api/listings`,
      },
      {
        source: '/api/listings/:id(\\d+)',
        destination: `${BACKEND_URL}/api/listings/:id`,
      },
      {
        source: '/api/listings/:id(\\d+)/photos',
        destination: `${BACKEND_URL}/api/listings/:id/photos`,
      },
      {
        source: '/api/listings/:id(\\d+)/photos/:path*',
        destination: `${BACKEND_URL}/api/listings/:id/photos/:path*`,
      },
      {
        source: '/api/listings/:id(\\d+)/buyer-intelligence',
        destination: `${BACKEND_URL}/api/listings/:id/buyer-intelligence`,
      },
      {
        source: '/api/listings/:id(\\d+)/buyer-intelligence/:path*',
        destination: `${BACKEND_URL}/api/listings/:id/buyer-intelligence/:path*`,
      },
      {
        source: '/api/listings/:id(\\d+)/photo-clusters',
        destination: `${BACKEND_URL}/api/listings/:id/photo-clusters`,
      },
      {
        source: '/api/listings/:id(\\d+)/photo-clusters/:path*',
        destination: `${BACKEND_URL}/api/listings/:id/photo-clusters/:path*`,
      },
      {
        source: '/api/listings/:id(\\d+)/room-analyses',
        destination: `${BACKEND_URL}/api/listings/:id/room-analyses`,
      },
      {
        source: '/api/listings/:id(\\d+)/room-analyses/:path*',
        destination: `${BACKEND_URL}/api/listings/:id/room-analyses/:path*`,
      },
      {
        source: '/api/listings/:id(\\d+)/due-diligence',
        destination: `${BACKEND_URL}/api/listings/:id/due-diligence`,
      },
      {
        source: '/api/listings/:id(\\d+)/home-condition',
        destination: `${BACKEND_URL}/api/listings/:id/home-condition`,
      },
      {
        source: '/api/listings/:id(\\d+)/home-condition/:path*',
        destination: `${BACKEND_URL}/api/listings/:id/home-condition/:path*`,
      },
      {
        source: '/api/listings/:id(\\d+)/pipeline',
        destination: `${BACKEND_URL}/api/listings/:id/pipeline`,
      },
      {
        source: '/api/listings/:id(\\d+)/pipeline/:path*',
        destination: `${BACKEND_URL}/api/listings/:id/pipeline/:path*`,
      },
      {
        source: '/api/listings/:id(\\d+)/pipeline-status',
        destination: `${BACKEND_URL}/api/listings/:id/pipeline-status`,
      },
      // V2/V5 pipeline endpoints
      {
        source: '/api/listings/:id(\\d+)/v2/:path*',
        destination: `${BACKEND_URL}/api/listings/:id/v2/:path*`,
      },
    ];
  },
};

export default nextConfig;
