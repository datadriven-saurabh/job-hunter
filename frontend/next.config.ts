import type { NextConfig } from 'next';
process.env.NEXT_TELEMETRY_DISABLED = '1';
const config: NextConfig = {
  poweredByHeader: false,
  async headers() {
    return [{source: '/:path*', headers: [
      {key: 'X-Content-Type-Options', value: 'nosniff'},
      {key: 'X-Frame-Options', value: 'DENY'},
      {key: 'Referrer-Policy', value: 'no-referrer'},
      {key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()'},
      {key: 'Content-Security-Policy', value: "frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'"},
    ]}];
  },
};
export default config;
