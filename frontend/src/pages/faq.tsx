import Head from 'next/head';
import { useState } from 'react';

const FAQS = [
  {
    q: 'How long are my files stored?',
    a: 'Uploaded files and generated artifacts are kept only for processing and download, then removed automatically after 60 minutes. Download your result promptly once the job completes.',
  },
  {
    q: 'Are my files secure?',
    a: 'Yes. File transfer is protected in transit, processing is temporary, and result downloads are delivered using signed job-specific links. PdfORBIT is designed around short-lived storage rather than permanent document hosting.',
  },
  {
    q: 'Do I need an account to use PdfORBIT?',
    a: 'For the current production workflow, you should expect to log in before uploading and processing files. This keeps job history, credits, downloads, and rate limits tied to your account securely.',
  },
  {
    q: 'Can I use PdfORBIT via API?',
    a: 'Not yet. The public API is still being prepared, and the API Docs page is a placeholder for the upcoming developer program.',
  },
  {
    q: 'Which languages does OCR support?',
    a: 'OCR support depends on installed language packs and the source document quality. English support is available today, and clear scans generally produce the best results.',
  },
  {
    q: 'Does translation preserve layout?',
    a: 'The translation pipeline tries to preserve readable structure, but complex layouts, tables, handwriting, and image-heavy pages may still be simplified in the final output.',
  },
  {
    q: 'How do AI summary jobs work?',
    a: 'Orbit Brief extracts text from the uploaded PDF, uses OCR when direct extraction is not enough, then sends the extracted text to the configured AI provider to build a concise summary PDF.',
  },
  {
    q: 'Where can I get support?',
    a: 'If you need help or have questions, you can contact us at support@pdforbit.app. We aim to respond to all support requests as quickly as possible.',
  },
];

export default function FAQ() {
  const [open, setOpen] = useState<number | null>(null);

  return (
    <>
      <Head>
        <title>FAQ — PdfORBIT</title>
        <meta name="description" content="Frequently asked questions about PdfORBIT." />
      </Head>
      <div className="static-page">
        <div className="static-hero">
          <div className="wrap">
            <div className="static-hero-inner">
              <div className="tag">// FAQ</div>
              <h1>Frequently Asked Questions</h1>
              <p>Everything you need to know about PdfORBIT as it runs today. Can&apos;t find an answer? Reach us at <a href="mailto:support@pdforbit.app" style={{ color: 'var(--red)' }}>support@pdforbit.app</a>.</p>
            </div>
          </div>
        </div>
        <div className="static-body">
          <div className="wrap">
            <div className="faq-list">
              {FAQS.map((faq, i) => (
                <div key={i} className={`faq-item${open === i ? ' open' : ''}`} onClick={() => setOpen(open === i ? null : i)}>
                  <div className="faq-q">
                    <span>{faq.q}</span>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16" style={{ transform: open === i ? 'rotate(180deg)' : 'none', transition: 'transform .2s' }}>
                      <path d="M6 9l6 6 6-6"/>
                    </svg>
                  </div>
                  {open === i && <div className="faq-a">{faq.a}</div>}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
