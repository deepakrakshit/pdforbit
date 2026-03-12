import { getToolFaqItems, type ToolSeoEntry } from '@/lib/seo/tools';
import type { BlogPost } from '@/lib/seo/blog';
import type { LandingPage } from '@/lib/seo/landings';
import type { ComparisonPage } from '@/lib/seo/comparisons';
import { SITE_LOGO_PATH, SITE_NAME, SITE_SUPPORT_EMAIL, SITE_URL, absoluteUrl } from '@/lib/seo/site';

function breadcrumbItem(position: number, name: string, path: string) {
  return {
    '@type': 'ListItem',
    position,
    name,
    item: absoluteUrl(path),
  };
}

export function buildSiteGraph() {
  return {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'Organization',
        '@id': `${SITE_URL}/#organization`,
        name: SITE_NAME,
        url: SITE_URL,
        email: SITE_SUPPORT_EMAIL,
        logo: {
          '@type': 'ImageObject',
          url: absoluteUrl(SITE_LOGO_PATH),
        },
        contactPoint: [
          {
            '@type': 'ContactPoint',
            contactType: 'customer support',
            email: SITE_SUPPORT_EMAIL,
          },
        ],
      },
      {
        '@type': 'WebSite',
        '@id': `${SITE_URL}/#website`,
        url: SITE_URL,
        name: SITE_NAME,
        publisher: {
          '@id': `${SITE_URL}/#organization`,
        },
      },
      {
        '@type': 'WebApplication',
        '@id': `${SITE_URL}/#webapp`,
        url: SITE_URL,
        name: SITE_NAME,
        applicationCategory: 'BusinessApplication',
        operatingSystem: 'Web',
        offers: {
          '@type': 'Offer',
          price: '0',
          priceCurrency: 'USD',
        },
      },
    ],
  };
}

export function buildToolSchemas(entry: ToolSeoEntry) {
  const faq = getToolFaqItems(entry.tool.id);

  return [
    {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [
        breadcrumbItem(1, SITE_NAME, '/'),
        breadcrumbItem(2, 'Tools', '/tools'),
        breadcrumbItem(3, entry.tool.name, entry.path),
      ],
    },
    {
      '@context': 'https://schema.org',
      '@type': 'HowTo',
      name: entry.heroTitle,
      step: entry.steps.map((text, index) => ({
        '@type': 'HowToStep',
        position: index + 1,
        text,
      })),
    },
    {
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: faq.map((item) => ({
        '@type': 'Question',
        name: item.q,
        acceptedAnswer: {
          '@type': 'Answer',
          text: item.a,
        },
      })),
    },
    {
      '@context': 'https://schema.org',
      '@type': 'SoftwareApplication',
      name: entry.tool.name,
      applicationCategory: 'BusinessApplication',
      operatingSystem: 'Web',
      offers: {
        '@type': 'Offer',
        price: '0',
        priceCurrency: 'USD',
      },
      description: entry.description,
      url: absoluteUrl(entry.path),
    },
  ];
}

export function buildBlogSchemas(post: BlogPost) {
  return [
    {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [
        breadcrumbItem(1, SITE_NAME, '/'),
        breadcrumbItem(2, 'Blog', '/blog'),
        breadcrumbItem(3, post.title, `/blog/${post.slug}`),
      ],
    },
    {
      '@context': 'https://schema.org',
      '@type': 'Article',
      headline: post.title,
      description: post.description,
      datePublished: post.publishedAt,
      dateModified: post.updatedAt,
      author: {
        '@type': 'Organization',
        name: SITE_NAME,
      },
      publisher: {
        '@type': 'Organization',
        name: SITE_NAME,
      },
      mainEntityOfPage: absoluteUrl(`/blog/${post.slug}`),
    },
  ];
}

export function buildLandingSchemas(page: LandingPage) {
  return [
    {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [breadcrumbItem(1, SITE_NAME, '/'), breadcrumbItem(2, page.title, `/${page.slug}`)],
    },
    {
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: page.faq.map((item) => ({
        '@type': 'Question',
        name: item.question,
        acceptedAnswer: {
          '@type': 'Answer',
          text: item.answer,
        },
      })),
    },
  ];
}

export function buildComparisonSchemas(page: ComparisonPage) {
  return [
    {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [
        breadcrumbItem(1, SITE_NAME, '/'),
        breadcrumbItem(2, 'Comparisons', '/compare'),
        breadcrumbItem(3, page.title, `/compare/${page.slug}`),
      ],
    },
    {
      '@context': 'https://schema.org',
      '@type': 'WebPage',
      name: page.title,
      description: page.description,
      about: [SITE_NAME, page.competitor],
    },
  ];
}