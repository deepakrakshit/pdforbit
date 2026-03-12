export const SITE_NAME = 'PdfORBIT';
export const SITE_URL = 'https://pdforbit.app';
export const SITE_SUPPORT_EMAIL = 'support@pdforbit.app';
export const SITE_TAGLINE = 'All your PDFs. One orbit.';
export const SITE_DEFAULT_TITLE = 'PdfORBIT | Free PDF Tools Online';
export const SITE_DEFAULT_DESCRIPTION = 'Free online PDF tools to merge, split, compress, convert, OCR, translate, and edit PDFs with fast, secure browser-based workflows.';
export const SITE_DEFAULT_OG_IMAGE = '/og/default.svg';
export const SITE_LOGO_PATH = '/brand/pdforbit-logo.svg';
export const SITE_LOGO_MARK_PATH = '/brand/pdforbit-mark.svg';

export const INDEXABLE_STATIC_PATHS = [
  '/',
  '/pricing',
  '/enterprise',
  '/about',
  '/contact',
  '/faq',
  '/api-docs',
  '/changelog',
];

export const NOINDEX_PATHS = [
  '/login',
  '/signup',
  '/dashboard',
  '/status',
];

export function absoluteUrl(path: string): string {
  return new URL(path, SITE_URL).toString();
}

export function normalizePath(path: string): string {
  if (!path || path === '/') {
    return '/';
  }

  return path.endsWith('/') ? path.slice(0, -1) : path;
}