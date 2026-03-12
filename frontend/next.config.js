const { LANDING_ROUTE_SLUGS, TOOL_ROUTE_MAP } = require('./seo.config.js');

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  eslint: {
    ignoreDuringBuilds: true,
  },
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
  },
  async redirects() {
    return [
      ...Object.entries(TOOL_ROUTE_MAP).map(([id, slug]) => ({
        source: `/tool/${id}`,
        destination: `/tools/${slug}`,
        permanent: true,
      })),
      {
        source: '/landing/:slug',
        destination: '/:slug',
        permanent: true,
      },
    ];
  },
  async rewrites() {
    return {
      beforeFiles: LANDING_ROUTE_SLUGS.map((slug) => ({
        source: `/${slug}`,
        destination: `/landing/${slug}`,
      })),
    };
  },
};

module.exports = nextConfig;
