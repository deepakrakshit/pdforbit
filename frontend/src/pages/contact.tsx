import Head from 'next/head';

export default function ContactPage() {
  return (
    <>
      <Head>
        <title>Contact — PdfORBIT</title>
        <meta name="description" content="Contact PdfORBIT support and product team." />
      </Head>
      <div className="static-page">
        <div className="static-hero">
          <div className="wrap">
            <div className="static-hero-inner">
              <div className="tag">// Contact</div>
              <h1>Contact Mission Control</h1>
              <p>Support, enterprise discussions, rollout questions, and general product feedback all come through the same inbox right now.</p>
            </div>
          </div>
        </div>
        <div className="static-body">
          <div className="wrap">
            <div className="contact-grid">
              <section className="contact-card">
                <h3>Email support</h3>
                <p className="contact-primary"><a href="mailto:support@pdforbit.app">support@pdforbit.app</a></p>
                <p>Use this for support issues, bug reports, partnership questions, enterprise requests, or follow-up on product feedback.</p>
              </section>
              <section className="contact-card">
                <h3>What to include</h3>
                <ul>
                  <li>The tool you were using</li>
                  <li>A short description of the issue or request</li>
                  <li>Your expected outcome</li>
                  <li>Any relevant job ID or screenshot</li>
                </ul>
              </section>
            </div>

            <div className="prose-section">
              <h2>Support note</h2>
              <p>PdfORBIT currently handles support through direct email rather than a public ticket portal. That keeps communication simple while the platform continues to expand.</p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}