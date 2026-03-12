import Link from 'next/link';
import { getAllToolSeoEntries } from '@/lib/seo/tools';
import { buildMetadata } from '@/lib/seo/metadata';

export const metadata = buildMetadata({
  title: 'PDF Tools Directory | PdfORBIT',
  description: 'Browse PdfORBIT’s full directory of PDF tools for merge, split, compress, convert, OCR, edit, translate, and security workflows.',
  path: '/tools',
  keywords: ['pdf tools', 'free pdf tools online', 'merge split compress pdf'],
});

export default function ToolsIndexPage() {
  const tools = getAllToolSeoEntries();

  return (
    <div className="static-page">
      <div className="static-hero">
        <div className="wrap">
          <div className="static-hero-inner">
            <div className="tag">// Tool directory</div>
            <h1>Browse every PdfORBIT tool</h1>
            <p>Structured for search, built for workflows, and ready to scale across conversion, editing, OCR, security, and programmatic landing pages.</p>
          </div>
        </div>
      </div>
      <div className="static-body">
        <div className="wrap">
          <div className="tools-grid" role="list">
            {tools.map((entry) => (
              <Link key={entry.tool.id} className="tool-card" href={entry.path}>
                <div className="tool-icon">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.7"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    dangerouslySetInnerHTML={{ __html: entry.tool.svg }}
                  />
                </div>
                <div className="tool-name">{entry.tool.name}</div>
                <div className="tool-desc">{entry.description}</div>
                <div className="tool-arrow">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M5 12h14m-7-7l7 7-7 7" />
                  </svg>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}