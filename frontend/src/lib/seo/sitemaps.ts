import { getAllBlogPosts } from '@/lib/seo/blog';
import { getAllLandingPages } from '@/lib/seo/landings';
import { getAllToolSeoEntries } from '@/lib/seo/tools';
import { INDEXABLE_STATIC_PATHS, SITE_URL, absoluteUrl } from '@/lib/seo/site';

export type SitemapEntry = {
  loc: string;
  lastmod?: string;
  changefreq?: 'daily' | 'weekly' | 'monthly';
  priority?: number;
};

function todayIso(): string {
  return new Date().toISOString();
}

export function getStaticSitemapEntries(): SitemapEntry[] {
  return INDEXABLE_STATIC_PATHS.map((path) => ({
    loc: absoluteUrl(path),
    lastmod: todayIso(),
    changefreq: path === '/' ? 'daily' : 'weekly',
    priority: path === '/' ? 1 : 0.7,
  }));
}

export function getToolSitemapEntries(): SitemapEntry[] {
  return getAllToolSeoEntries().map((entry) => ({
    loc: absoluteUrl(entry.path),
    lastmod: todayIso(),
    changefreq: 'weekly',
    priority: 0.9,
  }));
}

export function getBlogSitemapEntries(): SitemapEntry[] {
  return getAllBlogPosts().map((post) => ({
    loc: absoluteUrl(`/blog/${post.slug}`),
    lastmod: post.updatedAt,
    changefreq: 'monthly',
    priority: 0.7,
  }));
}

export function getLandingSitemapEntries(): SitemapEntry[] {
  return getAllLandingPages().map((page) => ({
    loc: absoluteUrl(`/${page.slug}`),
    lastmod: todayIso(),
    changefreq: 'weekly',
    priority: 0.8,
  }));
}

export function renderUrlSet(entries: SitemapEntry[]): string {
  const body = entries
    .map((entry) => `
  <url>
    <loc>${entry.loc}</loc>${entry.lastmod ? `
    <lastmod>${entry.lastmod}</lastmod>` : ''}${entry.changefreq ? `
    <changefreq>${entry.changefreq}</changefreq>` : ''}${typeof entry.priority === 'number' ? `
    <priority>${entry.priority.toFixed(1)}</priority>` : ''}
  </url>`)
    .join('');

  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${body}
</urlset>`;
}

export function renderSitemapIndex(paths: string[]): string {
  const body = paths
    .map((path) => `
  <sitemap>
    <loc>${new URL(path, SITE_URL).toString()}</loc>
    <lastmod>${todayIso()}</lastmod>
  </sitemap>`)
    .join('');

  return `<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${body}
</sitemapindex>`;
}