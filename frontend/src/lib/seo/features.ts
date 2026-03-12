export interface FeaturePage {
  slug: string;
  title: string;
  description: string;
  headline: string;
  intro: string;
  relatedToolIds: string[];
}

const FEATURE_PAGES: FeaturePage[] = [
  {
    slug: 'pdf-editor',
    title: 'Online PDF Editor',
    description: 'Edit PDFs online with text, highlights, images, signatures, and page-level changes.',
    headline: 'Edit PDFs online without leaving the browser.',
    intro: 'The editor feature page explains the core editing surface, common workflows, and the adjacent tools users typically need next.',
    relatedToolIds: ['editor', 'sign', 'ocr'],
  },
  {
    slug: 'ocr-pdf',
    title: 'OCR PDF Technology',
    description: 'Understand how PdfORBIT handles OCR workflows for scanned and image-heavy PDFs.',
    headline: 'OCR infrastructure for scanned and image-based PDFs.',
    intro: 'This feature page exists to capture OCR-focused search intent, explain the processing model, and link users into the right conversion and editing workflows.',
    relatedToolIds: ['ocr', 'pdf2word', 'translate'],
  },
];

export function getAllFeaturePages(): FeaturePage[] {
  return FEATURE_PAGES;
}

export function getFeaturePageBySlug(slug: string): FeaturePage | null {
  return FEATURE_PAGES.find((page) => page.slug === slug) ?? null;
}