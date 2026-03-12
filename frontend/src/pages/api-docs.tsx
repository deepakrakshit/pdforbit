import Head from 'next/head';

export default function ApiDocsPage() {
  return (
    <>
      <Head>
        <title>API Docs — PdfORBIT</title>
        <meta name="description" content="Preview the upcoming PdfORBIT developer API and integration roadmap." />
      </Head>
      <div className="static-page">
        <div className="static-hero">
          <div className="wrap">
            <div className="static-hero-inner">
              <div className="tag">// Developer Access</div>
              <h1>PdfORBIT API is on final approach</h1>
              <p>The public API is not open yet, but this page outlines the direction for authentication, endpoints, and developer onboarding.</p>
            </div>
          </div>
        </div>
        <div className="static-body">
          <div className="wrap">
            <div className="resource-grid">
              <section className="resource-card">
                <h3>Overview</h3>
                <p>The upcoming PdfORBIT API will expose secure document-processing workflows for uploads, job submission, status polling, and signed result downloads.</p>
              </section>
              <section className="resource-card">
                <h3>Authentication</h3>
                <p>Coming Soon. Developer authentication and access tokens will be documented here once public access is enabled.</p>
              </section>
              <section className="resource-card">
                <h3>Endpoints</h3>
                <p>Coming Soon. Planned endpoint families include uploads, organize, optimize, convert, edit, security, and intelligence workflows.</p>
              </section>
              <section className="resource-card">
                <h3>Developer access</h3>
                <p>Early enterprise or partner access will be coordinated manually during rollout. Reach out if you need API planning conversations before the public launch.</p>
              </section>
            </div>

            <div className="prose-section">
              <h2>Current status</h2>
              <p>The backend already runs a production API for the PdfORBIT web application, but public documentation, auth flows, and external onboarding are still being prepared.</p>
              <p>For early questions, contact <a href="mailto:support@pdforbit.app">support@pdforbit.app</a>.</p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}