import Head from 'next/head';

const RELEASES = [
  {
    version: 'v0.1.0',
    date: 'March 2026',
    title: 'Document intelligence launch',
    summary: 'AI-assisted translation and Orbit Brief summarization arrived alongside stronger OCR-aware extraction for image-heavy PDFs.',
    bullets: [
      'Added Translate PDF with OCR-assisted text extraction for scanned documents.',
      'Added Orbit Brief for executive-style PDF summaries.',
      'Introduced tool-specific backend modules and cleaner processor wiring.',
    ],
  },
  {
    version: 'v0.0.9',
    date: 'March 2026',
    title: 'Platform hardening and deployment cleanup',
    summary: 'Backend and frontend deploy flows were stabilized for Railway, including service-root fixes for the monorepo setup.',
    bullets: [
      'Fixed Railway deploy packaging for separate frontend and backend services.',
      'Improved startup configuration for production environments.',
      'Refined error pages and surfaced clearer job failures in the UI.',
    ],
  },
  {
    version: 'v0.0.8',
    date: 'March 2026',
    title: 'Compression and internal admin updates',
    summary: 'Compression profiles were tuned for more predictable output sizes and development workflows gained an internal admin bypass path.',
    bullets: [
      'Reworked PDF compression tiers for clearer behavior between quality levels.',
      'Added internal admin account support for testing without credit exhaustion.',
      'Updated dashboard and auth surfaces for admin-aware credit display.',
    ],
  },
];

export default function ChangelogPage() {
  return (
    <>
      <Head>
        <title>Changelog — PdfORBIT</title>
        <meta name="description" content="Track recent PdfORBIT releases, product improvements, and platform updates." />
      </Head>
      <div className="static-page">
        <div className="static-hero">
          <div className="wrap">
            <div className="static-hero-inner">
              <div className="tag">// Changelog</div>
              <h1>Release Notes from Mission Control</h1>
              <p>Recent product updates, infrastructure improvements, and feature launches across the PdfORBIT platform.</p>
            </div>
          </div>
        </div>
        <div className="static-body">
          <div className="wrap">
            <div className="timeline-list">
              {RELEASES.map((release) => (
                <article key={release.version} className="timeline-item">
                  <div className="timeline-meta">{release.version} · {release.date}</div>
                  <h3>{release.title}</h3>
                  <p>{release.summary}</p>
                  <ul>
                    {release.bullets.map((bullet) => <li key={bullet}>{bullet}</li>)}
                  </ul>
                </article>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}