import { getBlogSitemapEntries, renderUrlSet } from '@/lib/seo/sitemaps';

export function GET() {
  const xml = renderUrlSet(getBlogSitemapEntries());

  return new Response(xml, {
    headers: {
      'Content-Type': 'application/xml; charset=utf-8',
      'Cache-Control': 'public, s-maxage=3600, stale-while-revalidate=86400',
    },
  });
}