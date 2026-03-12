export interface FaqItem {
  q: string;
  a: string;
}

export const FAQ_ITEMS: FaqItem[] = [
  {
    q: 'Is PdfORBIT completely free?',
    a: 'PdfORBIT offers a free tier, but the current production workflow is account-based. You should expect to sign in before uploading files so jobs, downloads, and usage controls stay tied to your account.',
  },
  {
    q: 'How secure are my files?',
    a: 'Files are transferred securely, processed temporarily, and exposed through signed result links. Uploaded files and generated artifacts are scheduled for deletion after 60 minutes rather than retained indefinitely.',
  },
  {
    q: 'What file formats are supported?',
    a: 'PdfORBIT focuses on PDF processing and supports common document and image formats used with PDFs, including DOCX, XLSX, PPTX, JPG, PNG, and other standard formats depending on the tool being used.',
  },
  {
    q: 'How does OCR work?',
    a: 'OCR (Optical Character Recognition) converts text inside scanned images or PDFs into selectable and searchable text. The system analyzes each page and generates a new PDF containing both the original visuals and a text layer for searching and copying.',
  },
  {
    q: 'How does translation work?',
    a: 'Translate PDF and Orbit Brief first extract readable document text, use OCR when scanned pages need it, and then send the extracted text to the configured AI provider before generating the output PDF.',
  },
  {
    q: 'What happens to my files after processing?',
    a: 'Uploaded files are used only for the requested job. After processing, results stay available briefly for download and are automatically deleted after 60 minutes.',
  },
  {
    q: 'Is there an API available?',
    a: 'Not yet. The public API is still in preparation, and the API Docs page currently serves as a placeholder for the upcoming developer rollout.',
  },
  {
    q: 'How long do AI jobs take?',
    a: 'OCR-heavy, image-heavy, or AI-assisted jobs can take longer than basic PDF operations because the platform has to extract text, run background processing, and then generate a new result file for download.',
  },
];