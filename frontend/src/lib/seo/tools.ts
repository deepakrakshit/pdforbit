import { getToolFaqs } from '@/data/toolFaqs';
import { TOOLS, type Tool } from '@/data/tools';
import { getToolPathById, getToolSlugById } from '@/lib/seo/routes';

export interface ToolSeoEntry {
  tool: Tool;
  slug: string;
  path: string;
  heroTitle: string;
  title: string;
  description: string;
  intro: string;
  steps: string[];
  benefits: string[];
  security: string;
  relatedToolIds: string[];
  guideSlugs: string[];
  keywords: string[];
  ogImage: string;
}

type ToolSeoOverride = Partial<Omit<ToolSeoEntry, 'tool' | 'slug' | 'path'>>;

const TOOL_SEO_OVERRIDES: Record<string, ToolSeoOverride> = {
  merge: {
    heroTitle: 'Merge PDF Online Free',
    title: 'Merge PDF Online Free | Combine PDF Files Fast | PdfORBIT',
    description: 'Combine multiple PDF files into one document online for free. Fast processing, clean output, and no unnecessary friction.',
    intro: 'Merge PDFs in the correct order, keep the workflow simple, and download one final document without rebuilding pages manually.',
    steps: ['Upload the PDFs you want to combine.', 'Arrange the file order for the final output.', 'Run the merge workflow and download the merged PDF.'],
    benefits: ['Combines multiple documents into one shareable file.', 'Preserves the original page layout during the merge workflow.', 'Supports adjacent workflows like compressing or splitting the merged output.'],
    security: 'Uploaded files are used for processing and then removed by the platform cleanup lifecycle. The merge workflow creates a fresh output file instead of modifying the originals in place.',
    relatedToolIds: ['split', 'compress', 'extract'],
    guideSlugs: ['how-to-merge-pdf', 'how-to-compress-pdf'],
    keywords: ['merge pdf online free', 'combine pdf files', 'merge pdf without watermark'],
  },
  compress: {
    heroTitle: 'Compress PDF Online Free',
    title: 'Compress PDF Online Free | Reduce PDF File Size | PdfORBIT',
    description: 'Reduce PDF file size online for email, uploads, and storage while keeping documents readable.',
    intro: 'Compress PDFs with output-size intent in mind, whether the goal is faster sharing, a portal upload limit, or smaller archive files.',
    steps: ['Upload the PDF you need to shrink.', 'Choose the compression level or preset that fits the use case.', 'Process and review the smaller output before sending it onward.'],
    benefits: ['Makes large PDFs easier to email and upload.', 'Creates smaller files for storage and faster sharing.', 'Supports related landing pages for size-specific outcomes like 1MB and 500KB targets.'],
    security: 'Compression runs as a processing job tied to the authenticated session. Files are held temporarily for conversion and download, then removed through cleanup.',
    relatedToolIds: ['merge', 'pdf2img', 'split'],
    guideSlugs: ['how-to-compress-pdf', 'how-to-merge-pdf'],
    keywords: ['compress pdf online free', 'reduce pdf file size', 'pdf compressor'],
  },
  pdf2word: {
    heroTitle: 'PDF to Word Converter',
    title: 'PDF to Word Free Online | Convert PDF to Editable DOCX | PdfORBIT',
    description: 'Convert PDFs into editable Word documents online with layout-aware workflows and OCR support for scans.',
    intro: 'Turn PDFs into editable Word files when you need to revise contracts, reports, proposals, or other office documents.',
    steps: ['Upload the PDF document.', 'Run the PDF to Word workflow with OCR when needed.', 'Download the DOCX file and edit it in Word-compatible software.'],
    benefits: ['Produces editable office documents from PDFs.', 'Pairs with OCR for scan-heavy files.', 'Creates a clean path back to PDF after edits are finished.'],
    security: 'Conversion files are processed through the authenticated upload pipeline and made available only through the generated job result before cleanup.',
    relatedToolIds: ['ocr', 'word2pdf', 'editor'],
    guideSlugs: ['how-to-edit-pdf-online', 'how-to-compress-pdf'],
    keywords: ['pdf to word free', 'convert pdf to editable word', 'pdf to docx online'],
  },
  word2pdf: {
    heroTitle: 'Word to PDF Converter',
    title: 'Word to PDF Online Free | Convert DOCX to PDF | PdfORBIT',
    description: 'Convert Word documents into portable PDF files online for sharing, archiving, and final review.',
    intro: 'Create a stable PDF output from Word content when you need a document that looks consistent across devices and reviewers.',
    relatedToolIds: ['pdf2word', 'merge', 'protect'],
    guideSlugs: ['how-to-merge-pdf', 'how-to-compress-pdf'],
    keywords: ['word to pdf', 'docx to pdf online', 'convert word to pdf free'],
  },
  editor: {
    heroTitle: 'Edit PDF Online',
    title: 'Edit PDF Online Free | Add Text, Images, Highlights, and Signatures | PdfORBIT',
    description: 'Edit PDF files online with text, drawings, highlights, images, signatures, and page-level adjustments.',
    intro: 'The PdfORBIT editor is built for practical browser-based PDF changes: annotations, highlights, signatures, image placement, and page adjustments.',
    steps: ['Upload a PDF into the editor.', 'Apply text, highlight, shape, image, or signature changes page by page.', 'Export the updated file when the review is complete.'],
    benefits: ['Handles fast browser-based PDF revision workflows.', 'Supports markup, signatures, and visual edits without desktop software.', 'Connects naturally to OCR and export workflows for scanned documents.'],
    security: 'Editor sessions operate on uploaded files within the authenticated application flow. Files remain temporary and subject to cleanup after processing windows expire.',
    relatedToolIds: ['sign', 'ocr', 'rotate'],
    guideSlugs: ['how-to-edit-pdf-online', 'how-to-merge-pdf'],
    keywords: ['edit pdf online', 'pdf editor online free', 'annotate pdf online'],
  },
  ocr: {
    heroTitle: 'OCR PDF Online',
    title: 'OCR PDF Online | Make Scanned PDFs Searchable | PdfORBIT',
    description: 'Convert scanned PDFs into searchable, selectable text with OCR-based PDF processing.',
    intro: 'Use OCR when your PDF is really a set of images and you need to search, copy, summarize, translate, or convert the text inside it.',
    steps: ['Upload the scanned PDF.', 'Choose OCR settings such as language and resolution.', 'Run OCR and download the searchable output file.'],
    benefits: ['Makes scanned content searchable and selectable.', 'Improves downstream conversion into Word and translation workflows.', 'Unlocks text extraction for summaries and review.'],
    security: 'OCR processing follows the same temporary file lifecycle as other tools. Files are used for recognition, delivered through the job result, and removed afterward.',
    relatedToolIds: ['pdf2word', 'translate', 'summarize'],
    guideSlugs: ['how-to-edit-pdf-online', 'how-to-compress-pdf'],
    keywords: ['ocr pdf', 'make scanned pdf searchable', 'searchable pdf ocr'],
  },
  translate: {
    heroTitle: 'Translate PDF Online',
    title: 'Translate PDF Online | OCR-Powered PDF Translation | PdfORBIT',
    description: 'Translate PDF files with OCR-aware processing for scanned, image-heavy, and mixed-layout documents.',
    intro: 'Pdf translation often fails when tools ignore OCR and layout complexity. This workflow is designed to extract text, translate it, and rebuild a usable result.',
    relatedToolIds: ['ocr', 'summarize', 'editor'],
    guideSlugs: ['how-to-edit-pdf-online', 'how-to-compress-pdf'],
    keywords: ['translate pdf online', 'pdf translator', 'translate scanned pdf'],
  },
};

function defaultSteps(tool: Tool): string[] {
  return [
    `Upload the ${tool.accept.replace(/\./g, '').toUpperCase()} file required for ${tool.name}.`,
    `Configure the ${tool.name} options that fit the task.`,
    'Start processing and download the generated result when the job completes.',
  ];
}

function defaultBenefits(tool: Tool): string[] {
  return [
    tool.desc,
    `${tool.name} runs inside the existing PdfORBIT job-processing system for consistent uploads, status tracking, and downloads.`,
    `The workflow can be chained with related tools when users need broader document processing rather than a single step.`,
  ];
}

function defaultSecurity(tool: Tool): string {
  return `${tool.name} uses the authenticated upload pipeline and the same temporary-processing lifecycle as the rest of PdfORBIT. Files are stored only for job execution and download before scheduled cleanup removes them.`;
}

function defaultHeroTitle(tool: Tool): string {
  if (tool.name.toLowerCase().includes('pdf')) {
    return `${tool.name} Online`;
  }
  return `${tool.name} for PDF Workflows`;
}

function defaultTitle(tool: Tool): string {
  return `${tool.name} Online | PdfORBIT`;
}

function defaultDescription(tool: Tool): string {
  return `${tool.desc} Run ${tool.name.toLowerCase()} workflows online with secure uploads and downloadable results.`;
}

function defaultIntro(tool: Tool): string {
  return `${tool.desc} This page is part of PdfORBIT’s structured tool directory, built to help users understand the workflow before they upload, process, and download.`;
}

function defaultRelatedTools(toolId: string): string[] {
  const fallback = ['merge', 'compress', 'ocr', 'editor', 'pdf2word', 'sign'];
  return fallback.filter((candidate) => candidate !== toolId).slice(0, 3);
}

function defaultGuideSlugs(toolId: string): string[] {
  if (toolId === 'merge' || toolId === 'split') {
    return ['how-to-merge-pdf', 'how-to-compress-pdf'];
  }
  if (toolId === 'editor' || toolId === 'sign') {
    return ['how-to-edit-pdf-online', 'how-to-merge-pdf'];
  }
  return ['how-to-compress-pdf', 'how-to-edit-pdf-online'];
}

const TOOL_SEO_ENTRIES: ToolSeoEntry[] = TOOLS.map((tool) => {
  const override = TOOL_SEO_OVERRIDES[tool.id] ?? {};

  return {
    tool,
    slug: getToolSlugById(tool.id),
    path: getToolPathById(tool.id),
    heroTitle: override.heroTitle ?? defaultHeroTitle(tool),
    title: override.title ?? defaultTitle(tool),
    description: override.description ?? defaultDescription(tool),
    intro: override.intro ?? defaultIntro(tool),
    steps: override.steps ?? defaultSteps(tool),
    benefits: override.benefits ?? defaultBenefits(tool),
    security: override.security ?? defaultSecurity(tool),
    relatedToolIds: override.relatedToolIds ?? defaultRelatedTools(tool.id),
    guideSlugs: override.guideSlugs ?? defaultGuideSlugs(tool.id),
    keywords: override.keywords ?? [tool.name.toLowerCase(), `${tool.name.toLowerCase()} online`, `${tool.name.toLowerCase()} free`],
    ogImage: override.ogImage ?? `/og/tools/${getToolSlugById(tool.id)}.png`,
  };
});

export function getAllToolSeoEntries(): ToolSeoEntry[] {
  return TOOL_SEO_ENTRIES;
}

export function getToolSeoEntryBySlug(slug: string): ToolSeoEntry | null {
  return TOOL_SEO_ENTRIES.find((entry) => entry.slug === slug) ?? null;
}

export function getToolSeoEntryById(id: string): ToolSeoEntry | null {
  return TOOL_SEO_ENTRIES.find((entry) => entry.tool.id === id) ?? null;
}

export function getRelatedToolSeoEntries(toolId: string): ToolSeoEntry[] {
  const entry = getToolSeoEntryById(toolId);
  if (!entry) {
    return [];
  }

  return entry.relatedToolIds.map((id) => getToolSeoEntryById(id)).filter((value): value is ToolSeoEntry => Boolean(value));
}

export function getToolFaqItems(toolId: string) {
  const tool = TOOLS.find((candidate) => candidate.id === toolId);
  return tool ? getToolFaqs(tool) : [];
}