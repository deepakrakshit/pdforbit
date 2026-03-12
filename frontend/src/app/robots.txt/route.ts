import { SITE_URL } from '@/lib/seo/site';

export function GET() {
  const content = `User-agent: *
Allow: /
Disallow: /api/
Disallow: /_next/
Disallow: /dashboard
Disallow: /login
Disallow: /signup
Disallow: /status
Disallow: /uploads/
Disallow: /results/
Disallow: /jobs/

Sitemap: ${SITE_URL}/sitemap.xml
Host: ${SITE_URL}
`;

  return new Response(content, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'Cache-Control': 'public, s-maxage=3600, stale-while-revalidate=86400',
    },
  });
}