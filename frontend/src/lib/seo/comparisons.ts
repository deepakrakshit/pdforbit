export interface ComparisonPage {
  slug: string;
  title: string;
  description: string;
  headline: string;
  competitor: string;
  advantages: string[];
  relatedToolIds: string[];
}

const COMPARISON_PAGES: ComparisonPage[] = [
  {
    slug: 'ilovepdf-vs-pdforbit',
    title: 'iLovePDF vs PdfORBIT',
    description: 'Compare iLovePDF and PdfORBIT across free PDF tools, editing workflows, OCR, and conversion coverage.',
    headline: 'Compare iLovePDF and PdfORBIT across core PDF workflows.',
    competitor: 'iLovePDF',
    advantages: [
      'Cleaner long-tail landing-page coverage for workflow-specific search intent.',
      'A unified path from free tools into OCR, editing, translation, and enterprise workflows.',
      'A content model designed for deeper educational and problem-solving pages.',
    ],
    relatedToolIds: ['merge', 'compress', 'editor'],
  },
  {
    slug: 'smallpdf-vs-pdforbit',
    title: 'Smallpdf vs PdfORBIT',
    description: 'Compare Smallpdf and PdfORBIT across free usage, PDF editing, OCR, and platform flexibility.',
    headline: 'Compare Smallpdf and PdfORBIT for free and advanced PDF workflows.',
    competitor: 'Smallpdf',
    advantages: [
      'A stronger route taxonomy for tool pages, long-tail landings, and content-led acquisition.',
      'Programmatic SEO support for modifier queries like output-size and no-watermark intent.',
      'A tighter internal-linking system connecting guides, tools, and feature pages.',
    ],
    relatedToolIds: ['compress', 'pdf2word', 'ocr'],
  },
];

export function getAllComparisonPages(): ComparisonPage[] {
  return COMPARISON_PAGES;
}

export function getComparisonPageBySlug(slug: string): ComparisonPage | null {
  return COMPARISON_PAGES.find((page) => page.slug === slug) ?? null;
}