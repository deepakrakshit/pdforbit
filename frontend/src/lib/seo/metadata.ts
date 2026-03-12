import type { Metadata } from 'next';
import { SITE_DEFAULT_OG_IMAGE, SITE_DEFAULT_TITLE, SITE_LOGO_MARK_PATH, SITE_NAME, SITE_URL, absoluteUrl, normalizePath } from '@/lib/seo/site';

interface MetadataInput {
  title: string;
  description: string;
  path: string;
  keywords?: string[];
  image?: string;
  noindex?: boolean;
}

export function buildMetadata({ title, description, path, keywords = [], image = SITE_DEFAULT_OG_IMAGE, noindex = false }: MetadataInput): Metadata {
  const canonicalPath = normalizePath(path);
  const canonicalUrl = absoluteUrl(canonicalPath);

  return {
    metadataBase: new URL(SITE_URL),
    title,
    description,
    keywords,
    alternates: {
      canonical: canonicalPath,
    },
    robots: noindex
      ? {
          index: false,
          follow: false,
          googleBot: {
            index: false,
            follow: false,
          },
        }
      : {
          index: true,
          follow: true,
          googleBot: {
            index: true,
            follow: true,
            'max-image-preview': 'large',
            'max-snippet': -1,
            'max-video-preview': -1,
          },
        },
    openGraph: {
      type: 'website',
      url: canonicalUrl,
      siteName: SITE_NAME,
      title,
      description,
      images: [
        {
          url: image,
          width: 1200,
          height: 630,
          alt: title,
        },
      ],
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
      images: [image],
    },
  };
}

export const siteMetadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: SITE_DEFAULT_TITLE,
    template: `%s | ${SITE_NAME}`,
  },
  description: 'PdfORBIT is a search-optimized PDF SaaS platform with online tools for merging, splitting, compressing, converting, editing, OCR, translation, and enterprise workflows.',
  applicationName: SITE_NAME,
  manifest: '/site.webmanifest',
  icons: {
    icon: [
      { url: SITE_LOGO_MARK_PATH, type: 'image/svg+xml' },
    ],
    shortcut: [SITE_LOGO_MARK_PATH],
    apple: [{ url: SITE_LOGO_MARK_PATH, type: 'image/svg+xml' }],
  },
};