import Head from 'next/head';

const STATS = [
  { val: '30+', label: 'PDF tools' },
  { val: 'OCR + AI', label: 'Intelligence layer' },
  { val: '60 min', label: 'Auto-delete window' },
  { val: 'Online', label: 'No install required' },
];

export default function About() {
  return (
    <>
      <Head>
        <title>About — PdfORBIT</title>
        <meta name="description" content="Learn about PdfORBIT — the PDF platform built for developers and professionals." />
      </Head>
      <div className="static-page">
        <div className="static-hero">
          <div className="wrap">
            <div className="static-hero-inner">
              <div className="tag">// About</div>
              <h1>PDF Tools That Work at the Speed of Thought</h1>
              <p>PdfORBIT is a modern PDF processing platform built for fast uploads, background job execution, secure downloads, OCR workflows, and AI-assisted document tasks.</p>
            </div>
          </div>
        </div>
        <div className="static-body">
          <div className="wrap">

            {/* Stats */}
            <div className="stats-grid">
              {STATS.map(s => (
                <div key={s.label} className="stat-card">
                  <div className="stat-val">{s.val}</div>
                  <div className="stat-label">{s.label}</div>
                </div>
              ))}
            </div>

            {/* Mission */}
            <div className="prose-section">
              <h2>Our Mission</h2>
              <p>
                Documents power the modern world — contracts, invoices, research papers,
                legal agreements, reports, and presentations all rely on PDFs. Yet many
                tools designed to work with them are slow, cluttered, or unnecessarily
                complicated.
              </p>
              <p>
                PdfORBIT was created to make document processing simple, fast, and
                operationally reliable. The platform is designed around authenticated
                uploads, queue-backed workers, temporary storage, and signed downloads so
                users can run real document workflows without installing desktop software.
              </p>
            </div>

            {/* How it works */}
            <div className="prose-section">
              <h2>How It Works</h2>
              <p>
                PdfORBIT is designed around a straightforward processing pipeline. When a
                file is uploaded, it is stored temporarily, attached to a processing job,
                and handed to background workers that perform the requested operation —
                such as merging, compressing, converting, OCR, translation, or summarization.
              </p>
              <p>
                Once processing completes, the result is exposed through a signed download
                link. Uploaded files and generated artifacts are retained only for a short
                processing window and are automatically deleted after 60 minutes.
              </p>
            </div>

            {/* Team */}
            <div className="prose-section">
              <h2>Built for Real Work</h2>
              <p>
                PdfORBIT is built by developers who care about creating tools that solve
                real problems. Instead of focusing on unnecessary complexity, we focus on
                speed, reliability, and a clean user experience that still feels fast even
                when the backend is performing heavy document work behind the scenes.
              </p>
              <p>
                The platform continues to evolve as new document workflows emerge. Current
                roadmap work includes public API access, deeper enterprise controls, richer
                monitoring, and continued improvement of OCR and AI-powered document tools.
              </p>
              <p>
                Have feedback, a feature request, or discovered an issue? Reach us at{" "}
                <a
                  href="mailto:support@pdforbit.app"
                  style={{ color: "var(--red)" }}
                >
                  support@pdforbit.app
                </a>.
              </p>
            </div>

          </div>
        </div>
      </div>
    </>
  );
}
