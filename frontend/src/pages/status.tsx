import Head from 'next/head';

const SERVICES = [
  {
    name: 'PDF Processing',
    detail: 'Core organize, convert, optimize, and security tools are operating normally.',
  },
  {
    name: 'Uploads',
    detail: 'Authenticated uploads and temporary storage are available and accepting new jobs.',
  },
  {
    name: 'API',
    detail: 'The production API is reachable and serving the web application successfully.',
  },
  {
    name: 'Background workers',
    detail: 'Queue workers and cleanup tasks are online and processing jobs in the background.',
  },
];

export default function StatusPage() {
  return (
    <>
      <Head>
        <title>Status — PdfORBIT</title>
        <meta name="description" content="Check current PdfORBIT system status and service availability." />
        <meta name="robots" content="noindex,follow" />
      </Head>
      <div className="static-page">
        <div className="static-hero">
          <div className="wrap">
            <div className="static-hero-inner">
              <div className="tag">// System Status</div>
              <h1>All systems operational</h1>
              <p>Live service overview for core PdfORBIT systems. This page currently reflects a simple placeholder health board.</p>
            </div>
          </div>
        </div>
        <div className="static-body">
          <div className="wrap">
            <div className="status-pill">All systems operational</div>
            <div className="status-grid">
              {SERVICES.map((service) => (
                <section key={service.name} className="status-card">
                  <h3>{service.name}</h3>
                  <p>{service.detail}</p>
                </section>
              ))}
            </div>

            <div className="prose-section">
              <h2>Status note</h2>
              <p>This page is intentionally lightweight for now. A deeper public incident log and historical availability dashboard can be added once external status reporting becomes part of the product surface.</p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}