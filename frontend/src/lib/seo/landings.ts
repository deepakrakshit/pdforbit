export interface LandingPage {
  slug: string;
  title: string;
  description: string;
  hero: string;
  intro: string;
  toolId: string;
  useCase: string;
  preset: Record<string, string | number | boolean>;
  faq: Array<{ question: string; answer: string }>;
  relatedToolIds: string[];
  relatedGuideSlugs: string[];
  keywords: string[];
}

const LANDING_PAGES: LandingPage[] = [
  {
    slug: 'compress-pdf-to-1mb',
    title: 'Compress PDF to 1MB Online Free',
    description: 'Reduce PDF size for email and form uploads with a workflow tuned for 1MB targets.',
    hero: 'Compress PDF to 1MB online with a workflow tuned for upload limits and attachment rules.',
    intro: 'This landing page is built for one specific outcome: getting oversized PDFs under a common upload threshold without guessing at settings.',
    toolId: 'compress',
    useCase: 'Best for email attachments, government portals, and forms that reject larger files.',
    preset: { targetSize: '1mb', mode: 'balanced' },
    faq: [
      {
        question: 'Will every PDF reach exactly 1MB?',
        answer: 'No. The target depends on the original content, but this workflow is tuned to maximize the chance of getting close while keeping the document readable.',
      },
      {
        question: 'What types of PDFs compress best?',
        answer: 'Image-heavy and scanned PDFs usually compress more than text-first PDFs that are already relatively efficient.',
      },
    ],
    relatedToolIds: ['compress', 'merge', 'pdf2img'],
    relatedGuideSlugs: ['how-to-compress-pdf', 'how-to-merge-pdf'],
    keywords: ['compress pdf to 1mb', 'reduce pdf to 1mb', 'pdf compressor 1mb'],
  },
  {
    slug: 'compress-pdf-to-500kb',
    title: 'Compress PDF to 500KB Online',
    description: 'Shrink PDFs for strict upload limits with a 500KB-focused compression landing page.',
    hero: 'Compress PDF to 500KB for strict upload portals and lightweight document sharing.',
    intro: 'When standard compression is not enough, this landing page focuses on more aggressive size reduction for tighter limits.',
    toolId: 'compress',
    useCase: 'Best for high-friction submission portals and document workflows with very low maximum file sizes.',
    preset: { targetSize: '500kb', mode: 'aggressive' },
    faq: [
      {
        question: 'Does 500KB compression affect quality more than 1MB compression?',
        answer: 'Usually yes. More aggressive size reduction often requires stronger image optimization, so you should always review the final file before sending it.',
      },
      {
        question: 'Should I split the file instead of compressing harder?',
        answer: 'If readability drops too much, splitting the document or exporting selected pages can be the better workflow.',
      },
    ],
    relatedToolIds: ['compress', 'split', 'extract'],
    relatedGuideSlugs: ['how-to-compress-pdf', 'how-to-merge-pdf'],
    keywords: ['compress pdf to 500kb', 'reduce pdf to 500kb', 'pdf compressor 500kb'],
  },
  {
    slug: 'merge-pdf-without-watermark',
    title: 'Merge PDF Without Watermark',
    description: 'Combine PDFs into one file online without adding a forced watermark to the output.',
    hero: 'Merge PDF files online without watermark clutter in the final result.',
    intro: 'Many users search for this query because they do not want a free tool to brand client-ready documents. This workflow keeps the output clean.',
    toolId: 'merge',
    useCase: 'Useful for invoices, contracts, reports, and presentation packs that need a professional final file.',
    preset: { watermarkFree: true, mergeMode: 'ordered' },
    faq: [
      {
        question: 'Do I need an account to merge without watermark?',
        answer: 'You still need the normal product flow, but the key point is that the final merged document is not stamped with a promotional watermark.',
      },
      {
        question: 'Can I reorder files before merging?',
        answer: 'Yes. File order matters and should be set before you process the combined document.',
      },
    ],
    relatedToolIds: ['merge', 'split', 'compress'],
    relatedGuideSlugs: ['how-to-merge-pdf', 'how-to-compress-pdf'],
    keywords: ['merge pdf without watermark', 'merge pdf free no watermark', 'combine pdf without watermark'],
  },
  {
    slug: 'pdf-to-word-editable',
    title: 'Convert PDF to Editable Word',
    description: 'Turn PDFs into editable Word documents online with formatting-aware conversion workflows.',
    hero: 'Convert PDF to editable Word documents without rebuilding everything by hand.',
    intro: 'This landing page is focused on the intent behind editable conversion, not just file-format swapping. Users want usable content they can revise immediately.',
    toolId: 'pdf2word',
    useCase: 'Best for contracts, proposals, reports, and office documents that need post-conversion editing in DOCX.',
    preset: { outputFormat: 'docx', editableFocus: true },
    faq: [
      {
        question: 'Will tables and formatting stay intact?',
        answer: 'Layout preservation depends on the source PDF, but office-generated PDFs usually convert more cleanly than scans or image-based documents.',
      },
      {
        question: 'Do scanned PDFs need OCR first?',
        answer: 'If the PDF is image-based, OCR improves the chances of producing editable text in the final Word document.',
      },
    ],
    relatedToolIds: ['pdf2word', 'ocr', 'word2pdf'],
    relatedGuideSlugs: ['how-to-edit-pdf-online', 'how-to-compress-pdf'],
    keywords: ['pdf to word editable', 'convert pdf to editable word', 'pdf to docx editable'],
  },
  {
    slug: 'scan-pdf-to-searchable-pdf',
    title: 'Scan PDF to Searchable PDF',
    description: 'Convert scanned PDFs into searchable files with OCR-driven text extraction.',
    hero: 'Turn scanned PDFs into searchable documents with OCR-aware processing.',
    intro: 'This workflow exists for users who do not just want a PDF file. They want one they can search, copy from, and manage efficiently.',
    toolId: 'ocr',
    useCase: 'Best for scanned archives, contracts, receipts, and multi-page image-based documents.',
    preset: { ocr: true, output: 'searchable-pdf' },
    faq: [
      {
        question: 'Does searchable mean the PDF becomes editable?',
        answer: 'Not automatically. Searchable usually means a text layer is added for find, select, and copy actions. Editing depends on the next workflow step.',
      },
      {
        question: 'What improves OCR accuracy?',
        answer: 'Higher-resolution scans, upright pages, strong contrast, and clean source images all improve OCR extraction quality.',
      },
    ],
    relatedToolIds: ['ocr', 'pdf2word', 'editor'],
    relatedGuideSlugs: ['how-to-edit-pdf-online', 'how-to-compress-pdf'],
    keywords: ['scan pdf to searchable pdf', 'make scanned pdf searchable', 'ocr searchable pdf'],
  },
  {
    slug: 'compress-pdf-for-email',
    title: 'Compress PDF for Email',
    description: 'Shrink PDF files for email attachments without making the document unreadable.',
    hero: 'Compress PDF for email when attachment limits block otherwise-ready documents.',
    intro: 'This landing page targets the common workflow where a PDF is finished, but still too large to send through email or shared inbox systems.',
    toolId: 'compress',
    useCase: 'Best for proposals, signed agreements, scanned reports, and supporting documents that need to be attached quickly.',
    preset: { destination: 'email', mode: 'balanced', target: 'attachment-friendly' },
    faq: [
      {
        question: 'What email limit should I target?',
        answer: 'That depends on the provider, but keeping a PDF comfortably small reduces failure risk and makes the attachment easier to handle downstream.',
      },
      {
        question: 'Should I remove pages before compressing for email?',
        answer: 'Yes if the document includes unnecessary pages. Removing them first often reduces size naturally and improves readability for the recipient.',
      },
    ],
    relatedToolIds: ['compress', 'remove', 'merge'],
    relatedGuideSlugs: ['how-to-compress-pdf', 'how-to-remove-pages-from-pdf'],
    keywords: ['compress pdf for email', 'make pdf smaller for email', 'email pdf compressor'],
  },
  {
    slug: 'compress-pdf-without-losing-quality',
    title: 'Compress PDF Without Losing Quality',
    description: 'Reduce PDF file size while keeping charts, text, and scanned pages readable.',
    hero: 'Compress PDF without losing unnecessary quality when readability matters as much as file size.',
    intro: 'This page targets users who want smaller files but are explicitly worried about blurry text, weak charts, or over-compressed scans.',
    toolId: 'compress',
    useCase: 'Best for reports, contracts, diagrams, forms, and any PDF where document clarity matters after compression.',
    preset: { priority: 'quality', mode: 'light-to-balanced' },
    faq: [
      {
        question: 'Can compression ever be completely lossless?',
        answer: 'Sometimes there are limited gains without visible tradeoffs, but large file-size reductions often involve some optimization choices. The goal here is to keep the document usable, not chase the smallest possible output at all costs.',
      },
      {
        question: 'Which PDFs handle quality-preserving compression best?',
        answer: 'Office-generated PDFs often compress more predictably than dense photo scans, but both can benefit when the workflow is tuned for readability first.',
      },
    ],
    relatedToolIds: ['compress', 'pdf2img', 'ocr'],
    relatedGuideSlugs: ['how-to-compress-pdf', 'how-to-make-a-scanned-pdf-searchable'],
    keywords: ['compress pdf without losing quality', 'reduce pdf size without losing quality', 'high quality pdf compression'],
  },
  {
    slug: 'pdf-to-word-free',
    title: 'PDF to Word Free Online',
    description: 'Convert PDF files to editable Word documents online for free.',
    hero: 'Convert PDF to Word online for free when you need editable text instead of a locked final document.',
    intro: 'This page targets straightforward conversion intent from users who are ready to act now and want an editable DOCX output without friction.',
    toolId: 'pdf2word',
    useCase: 'Best for resumes, office documents, reports, contracts, and proposals that need revision after conversion.',
    preset: { output: 'docx', plan: 'free-flow' },
    faq: [
      {
        question: 'Can I use PDF to Word for free?',
        answer: 'Yes. This landing page exists specifically for free-intent searchers who want editable Word output from a PDF workflow.',
      },
      {
        question: 'Does this work better on office PDFs than on scanned files?',
        answer: 'Yes. Native PDFs with real text generally convert more cleanly, while scanned files benefit from OCR-aware processing first.',
      },
    ],
    relatedToolIds: ['pdf2word', 'ocr', 'word2pdf'],
      relatedGuideSlugs: ['how-to-convert-pdf-to-word', 'how-to-make-a-scanned-pdf-searchable'],
    keywords: ['pdf to word free', 'convert pdf to word free', 'free pdf to docx'],
  },
  {
    slug: 'pdf-to-jpg-high-quality',
    title: 'Convert PDF to JPG High Quality',
    description: 'Export PDF pages as high-quality JPG images for previews, presentations, and reuse.',
    hero: 'Convert PDF to JPG in high quality when page clarity matters more than the smallest possible image size.',
    intro: 'Many PDF-to-image searchers want sharp exported pages for slides, websites, or client review. This page targets that quality-focused intent.',
    toolId: 'pdf2img',
    useCase: 'Best for preview images, presentation inserts, visual review, and marketing or document screenshots.',
    preset: { format: 'jpg', quality: 'high', dpi: 200 },
    faq: [
      {
        question: 'What improves JPG export quality the most?',
        answer: 'Higher output resolution and quality settings help preserve smaller text and detailed diagrams in the resulting images.',
      },
      {
        question: 'Should I export PNG instead of JPG for some pages?',
        answer: 'Sometimes. JPG is widely useful, but image-heavy or fine-detail pages may benefit from different output settings depending on the use case.',
      },
    ],
    relatedToolIds: ['pdf2img', 'compress', 'img2pdf'],
    relatedGuideSlugs: ['how-to-convert-pdf-to-jpg', 'how-to-compress-pdf'],
    keywords: ['pdf to jpg high quality', 'convert pdf to jpg high quality', 'best pdf to jpg online'],
  },
  {
    slug: 'word-to-pdf-online-free',
    title: 'Word to PDF Online Free',
    description: 'Convert Word documents into PDF online for free with a clean final-document workflow.',
    hero: 'Convert Word to PDF online for free when you need a final document that looks stable everywhere.',
    intro: 'This page targets users who are not looking for editing. They want a polished PDF output from a DOCX file right now.',
    toolId: 'word2pdf',
    useCase: 'Best for shareable proposals, reports, contracts, and office documents that need final review or approval.',
    preset: { source: 'word', output: 'pdf', plan: 'free-flow' },
    faq: [
      {
        question: 'Why convert Word to PDF before sending?',
        answer: 'PDF is usually safer for final distribution because layout changes are less likely across devices, viewers, and email clients.',
      },
      {
        question: 'Can I merge the resulting PDFs afterward?',
        answer: 'Yes. Once converted, multiple PDFs can be combined into one file when you need a final document pack.',
      },
    ],
    relatedToolIds: ['word2pdf', 'merge', 'protect'],
      relatedGuideSlugs: ['how-to-edit-pdf-online', 'how-to-merge-pdf'],
    keywords: ['word to pdf online free', 'convert word to pdf free', 'docx to pdf online free'],
  },
  {
    slug: 'edit-pdf-text-online',
    title: 'Edit PDF Text Online',
    description: 'Open a PDF editing workflow online for text, markups, highlights, and other quick document changes.',
    hero: 'Edit PDF text online when the document needs a fast update without a full desktop editor setup.',
    intro: 'This page captures users who search specifically for PDF text editing, even when the broader workflow also includes highlights, shapes, or signatures.',
    toolId: 'editor',
    useCase: 'Best for corrections, markup passes, document review, and fast browser-based edits before export.',
    preset: { mode: 'text-first', review: true },
    faq: [
      {
        question: 'Can I only edit text, or can I add other changes too?',
        answer: 'The editor workflow supports broader document changes as well, including highlights, shapes, images, and signatures depending on the task.',
      },
      {
        question: 'Should scanned PDFs go through OCR first?',
        answer: 'Yes if you need better text-based workflows. OCR improves what can be searched or converted before broader editing steps.',
      },
    ],
    relatedToolIds: ['editor', 'ocr', 'sign'],
    relatedGuideSlugs: ['how-to-edit-pdf-online', 'how-to-make-a-scanned-pdf-searchable'],
    keywords: ['edit pdf text online', 'change text in pdf online', 'pdf text editor online'],
  },
  {
    slug: 'sign-pdf-online-free',
    title: 'Sign PDF Online Free',
    description: 'Add a visible signature to a PDF online without printing, signing by hand, and rescanning.',
    hero: 'Sign PDF online for free when you need a fast approval workflow inside the browser.',
    intro: 'This page captures direct action intent from users who want to sign a PDF immediately and do not want a desktop signing workflow.',
    toolId: 'sign',
    useCase: 'Best for contracts, intake forms, internal approvals, and client documents that need a signature now.',
    preset: { mode: 'visible-signature', plan: 'free-flow' },
    faq: [
      {
        question: 'Can I sign and then protect the PDF?',
        answer: 'Yes. Many workflows add the signature first and then protect the final document for controlled sharing.',
      },
      {
        question: 'Do I need to print the document first?',
        answer: 'No. The goal of this workflow is to avoid printing and rescanning when the document only needs a placed signature in the PDF itself.',
      },
    ],
    relatedToolIds: ['sign', 'editor', 'protect'],
    relatedGuideSlugs: ['how-to-sign-a-pdf-online', 'how-to-password-protect-a-pdf'],
    keywords: ['sign pdf online free', 'sign pdf online', 'add signature to pdf free'],
  },
  {
    slug: 'protect-pdf-with-password',
    title: 'Protect PDF with Password',
    description: 'Secure a PDF with password-based access control before sharing it externally.',
    hero: 'Protect PDF with password when sensitive documents need controlled access.',
    intro: 'This landing page targets users who already know what they want: a PDF protected by a password before it leaves their control.',
    toolId: 'protect',
    useCase: 'Best for contracts, HR documents, invoices, reports, and files being shared through lower-trust channels.',
    preset: { protection: 'password', encryption: 256 },
    faq: [
      {
        question: 'Can I unlock the file later?',
        answer: 'Yes, as long as you still have the correct password and use an unlock workflow on the protected output.',
      },
      {
        question: 'Should I protect before or after editing?',
        answer: 'Usually after. Finish content changes first, then secure the final version so the protected file is the one you actually intend to distribute.',
      },
    ],
    relatedToolIds: ['protect', 'unlock', 'sign'],
    relatedGuideSlugs: ['how-to-password-protect-a-pdf', 'how-to-sign-a-pdf-online'],
    keywords: ['protect pdf with password', 'password protect pdf online', 'secure pdf file'],
  },
  {
    slug: 'extract-pages-from-pdf-online',
    title: 'Extract Pages from PDF Online',
    description: 'Save selected PDF pages as a new file when you only need part of a larger document.',
    hero: 'Extract pages from PDF online when the final file should include only the pages that matter.',
    intro: 'This page captures practical extraction intent from users who know exactly which pages they want in the final output.',
    toolId: 'extract',
    useCase: 'Best for contracts, appendices, invoices, reports, and chapter-level document sharing.',
    preset: { mode: 'extract', target: 'selected-pages' },
    faq: [
      {
        question: 'Can I extract non-consecutive pages?',
        answer: 'Yes. Extraction can target selected pages and ranges rather than only one continuous section.',
      },
      {
        question: 'Should I extract before compressing?',
        answer: 'Often yes. If the final file needs only a subset of pages, extracting first can reduce size naturally and simplify later optimization.',
      },
    ],
    relatedToolIds: ['extract', 'split', 'remove'],
    relatedGuideSlugs: ['how-to-extract-pages-from-pdf', 'how-to-split-pdf'],
    keywords: ['extract pages from pdf online', 'extract pdf pages', 'save selected pages from pdf online'],
  },
  {
    slug: 'remove-pages-from-pdf-online',
    title: 'Remove Pages from PDF Online',
    description: 'Delete unwanted pages from a PDF and export a cleaner final document.',
    hero: 'Remove pages from PDF online when the document includes sections that should not stay in the final version.',
    intro: 'This page targets delete-page intent from users cleaning up PDFs for submission, sharing, or archive quality control.',
    toolId: 'remove',
    useCase: 'Best for removing blank pages, duplicates, internal notes, and unnecessary appendices before sharing a document.',
    preset: { mode: 'remove', output: 'clean-final-pdf' },
    faq: [
      {
        question: 'Can I remove several pages at once?',
        answer: 'Yes. Page-removal workflows can target multiple pages or ranges before the final PDF is generated.',
      },
      {
        question: 'Will removing pages shrink the file size too?',
        answer: 'Usually yes. Fewer pages often means a smaller PDF, especially before any additional compression step.',
      },
    ],
    relatedToolIds: ['remove', 'extract', 'compress'],
    relatedGuideSlugs: ['how-to-remove-pages-from-pdf', 'how-to-compress-pdf'],
    keywords: ['remove pages from pdf online', 'delete pages from pdf free', 'remove pdf pages online'],
  },
];

export function getAllLandingPages(): LandingPage[] {
  return LANDING_PAGES;
}

export function getLandingPageBySlug(slug: string): LandingPage | null {
  return LANDING_PAGES.find((page) => page.slug === slug) ?? null;
}