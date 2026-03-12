import seoConfig from '../../../seo.config.js';

type SeoConfigShape = {
  TOOL_ROUTE_MAP: Record<string, string>;
  LANDING_ROUTE_SLUGS: string[];
};

const { TOOL_ROUTE_MAP, LANDING_ROUTE_SLUGS } = seoConfig as SeoConfigShape;

export { TOOL_ROUTE_MAP, LANDING_ROUTE_SLUGS };

export function getToolSlugById(id: string): string {
  return TOOL_ROUTE_MAP[id] ?? id;
}

export function getToolIdBySlug(slug: string): string | null {
  const entry = Object.entries(TOOL_ROUTE_MAP).find(([, value]) => value === slug);
  return entry?.[0] ?? null;
}

export function getToolPathById(id: string): string {
  return `/tools/${getToolSlugById(id)}`;
}

export function getLegacyToolPathById(id: string): string {
  return `/tool/${id}`;
}

export function getLandingPath(slug: string): string {
  return `/${slug}`;
}

export function getInternalLandingPath(slug: string): string {
  return `/landing/${slug}`;
}

export function isLandingSlug(slug: string): boolean {
  return LANDING_ROUTE_SLUGS.includes(slug);
}