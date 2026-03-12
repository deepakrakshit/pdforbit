import type { Tool } from '@/data/tools';

export interface ToolFaqItem {
  q: string;
  a: string;
}

const SPECIFIC_FAQS: Record<string, ToolFaqItem[]> = {
  merge: [
    {
      q: 'Can I merge more than two PDFs?',
      a: 'Yes. Merge PDF accepts multiple uploaded files and combines them in the order you add them. If the order matters, upload or add files in the sequence you want in the final document.',
    },
    {
      q: 'Does merging change page quality?',
      a: 'Merging combines the source PDFs into one result file. It does not intentionally downscale pages or re-render the entire document unless the source file itself already contains issues.',
    },
    {
      q: 'What happens to the original PDFs?',
      a: 'The original uploads remain separate inputs for the job. PdfORBIT generates a new merged output file and leaves the sources untouched until automatic cleanup removes temporary files.',
    },
  ],
  split: [
    {
      q: 'Can I split by page ranges or fixed intervals?',
      a: 'Yes. Split PDF supports ranges and interval-based splitting depending on the options you choose in the tool panel.',
    },
    {
      q: 'Will split pages keep the original formatting?',
      a: 'Yes. Split jobs keep the original page content and formatting because the tool is separating existing PDF pages rather than rebuilding them from scratch.',
    },
    {
      q: 'Do I get one file or many files back?',
      a: 'Split jobs usually return multiple outputs based on the ranges or interval settings you choose. Download the generated result package as soon as it is ready because temporary results auto-delete after 60 minutes.',
    },
  ],
  compress: [
    {
      q: 'How much can Compress PDF reduce file size?',
      a: 'Compression results depend on the source PDF. Image-heavy documents typically shrink more than text-only files, while already-optimized PDFs may show smaller gains.',
    },
    {
      q: 'Will compression reduce visual quality?',
      a: 'Compression can trade some visual fidelity for a smaller file, especially on raster-heavy pages. Choose the level that matches your priority between size reduction and document quality.',
    },
    {
      q: 'Is the original PDF overwritten?',
      a: 'No. The compressor creates a new output file and keeps the source upload as a separate temporary input until cleanup removes it.',
    },
  ],
  ocr: [
    {
      q: 'When should I use OCR PDF?',
      a: 'Use OCR when your PDF contains scanned pages, screenshots, or image-based text that is not selectable in a normal viewer.',
    },
    {
      q: 'Does OCR change the original page appearance?',
      a: 'The goal is to preserve the visible page while adding a searchable text layer. Results are strongest when the source scan is sharp, upright, and high contrast.',
    },
    {
      q: 'Can OCR read handwritten notes?',
      a: 'It can attempt to, but handwritten recognition is less reliable than printed text. Clean scans with large, legible handwriting produce the best results.',
    },
  ],
  translate: [
    {
      q: 'How does Translate PDF work?',
      a: 'Translate PDF extracts text from each page, uses OCR for scanned content when needed, sends the extracted text to the configured AI provider, and rebuilds a readable PDF output in the target language.',
    },
    {
      q: 'Will complex layouts translate perfectly?',
      a: 'Not always. Multi-column layouts, dense tables, handwritten notes, or image-heavy pages may require some simplification in the translated output so the content stays readable.',
    },
    {
      q: 'Can I choose the source language?',
      a: 'Yes. You can provide a source language when you know it, or leave detection to the translation pipeline when the document language is uncertain.',
    },
  ],
  summarize: [
    {
      q: 'What is Orbit Brief?',
      a: 'Orbit Brief is PdfORBIT’s PDF summary tool. It extracts document text, uses OCR if needed, and creates a structured summary PDF for faster review.',
    },
    {
      q: 'Can I control the summary style?',
      a: 'Yes. The tool supports different summary lengths and an optional focus prompt so you can bias the output toward contracts, risks, action items, or other priorities.',
    },
    {
      q: 'Does summarizing work on scanned PDFs?',
      a: 'Yes, as long as the OCR layer can extract enough readable text. Clean scans and high-resolution source pages improve the final brief considerably.',
    },
  ],
  compare: [
    {
      q: 'What does Compare PDF return?',
      a: 'Compare PDF checks two documents side by side and reports page-level differences so you can identify what changed between versions.',
    },
    {
      q: 'Do both files need to have the same page count?',
      a: 'No. The comparison can still highlight when one document has pages the other does not, although the clearest results come from documents with similar structure.',
    },
    {
      q: 'Is Compare PDF best for text edits or visual changes?',
      a: 'It is most useful when you need to spot visible or page-level differences between two related versions of the same document.',
    },
  ],
  protect: [
    {
      q: 'What kind of protection does Protect PDF add?',
      a: 'Protect PDF applies password-based PDF security so the output file requires the credentials you set before it can be opened or managed.',
    },
    {
      q: 'Should I use both user and owner passwords?',
      a: 'If you need stronger control, yes. Using both lets you separate open-access credentials from higher-privilege permissions management.',
    },
    {
      q: 'Can I remove protection later?',
      a: 'Yes, if you still have the required password. Use Unlock PDF on the protected file when you need to remove the applied restriction.',
    },
  ],
  redact: [
    {
      q: 'Is redaction permanent?',
      a: 'That is the goal. Redact PDF is intended to remove sensitive content from the generated output rather than simply hide it visually.',
    },
    {
      q: 'Can I redact by keyword or pattern?',
      a: 'Yes. The tool supports keyword-based and pattern-based redaction options so you can target repeated names, IDs, or matching text fragments.',
    },
    {
      q: 'Should I review the result after redaction?',
      a: 'Absolutely. Always inspect the output before sharing it to confirm that every sensitive element you intended to remove is gone.',
    },
  ],
};

function buildGenericFaqs(tool: Tool): ToolFaqItem[] {
  const fileTypes = tool.accept.replace(/\./g, '').toUpperCase();

  return [
    {
      q: `What does ${tool.name} do?`,
      a: tool.desc,
    },
    {
      q: `What files can I upload for ${tool.name}?`,
      a: `${tool.name} accepts ${fileTypes} files based on the current tool configuration. Make sure the uploaded document matches the supported input types shown in the upload area.`,
    },
    {
      q: `Does ${tool.name} change my original file?`,
      a: `No. ${tool.name} generates a new result from your uploaded input. The source file is only kept temporarily for processing and automatic cleanup.`,
    },
    {
      q: tool.multi ? `Can I upload multiple files for ${tool.name}?` : `How quickly should I download my ${tool.name} result?`,
      a: tool.multi
        ? `${tool.name} supports multiple uploaded files. Add every input you want in the job before starting processing so the output reflects the full set.`
        : `Download the generated result as soon as the job finishes. PdfORBIT is designed for temporary processing, and job files are automatically deleted after 60 minutes.`,
    },
  ];
}

export function getToolFaqs(tool: Tool): ToolFaqItem[] {
  return SPECIFIC_FAQS[tool.id] ?? buildGenericFaqs(tool);
}