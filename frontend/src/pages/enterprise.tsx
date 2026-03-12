import Head from 'next/head';

const FEATURES = [
  {
    title: 'Enterprise features',
    body: 'Custom workflow guidance, controlled rollout conversations, and future-facing options for larger teams that need more than the public self-serve experience.',
  },
  {
    title: 'Security posture',
    body: 'PdfORBIT is designed around secure transport, temporary processing, signed downloads, AES-256 PDF protection capabilities, and automatic deletion after 60 minutes.',
  },
  {
    title: 'High-volume processing',
    body: 'The platform is built on background workers and queue-based job execution, which is the right foundation for high-volume document operations and heavier workflows.',
  },
  {
    title: 'Priority support',
    body: 'Enterprise engagement is the path for organizations that need tighter response expectations, rollout planning, and direct coordination on requirements.',
  },
];

export default function EnterprisePage() {
  return (
    <>
      <Head>
        <title>Enterprise — PdfORBIT</title>
        <meta name="description" content="Explore enterprise-grade PDF processing options for teams and organizations using PdfORBIT." />
      </Head>
      <div className="static-page">
        <div className="static-hero">
          <div className="wrap">
            <div className="static-hero-inner">
              <div className="tag">// Enterprise</div>
              <h1>Enterprise-grade PDF processing for organizations</h1>
              <p>PdfORBIT is built on a production-ready processing pipeline and is evolving toward stronger enterprise controls, high-volume workflows, and direct support paths.</p>
            </div>
          </div>
        </div>
        <div className="static-body">
          <div className="wrap">
            <div className="resource-grid">
              {FEATURES.map((feature) => (
                <section key={feature.title} className="resource-card">
                  <h3>{feature.title}</h3>
                  <p>{feature.body}</p>
                </section>
              ))}
            </div>

            <div className="prose-section">
              <h2>What enterprise conversations are for</h2>
              <p>Use the enterprise channel if you need scale planning, procurement discussions, future API access, tighter operational guarantees, or a roadmap conversation around document-processing requirements.</p>
            </div>

            <div className="contact-card" id="contact-sales-form">
              <h3>Contact sales / enterprise team</h3>
              <p>If your organization needs a deeper conversation, email <a href="mailto:support@pdforbit.app">support@pdforbit.app</a> and include your expected document volume, workflow type, and timeline.</p>
              <form action="mailto:support@pdforbit.app" method="post" encType="text/plain" className="contact-sales-form">
                <div className="contact-sales-grid">
                  <label className="contact-sales-field">
                    <span>Name</span>
                    <input type="text" name="name" placeholder="Jane Doe" required />
                  </label>
                  <label className="contact-sales-field">
                    <span>Work email</span>
                    <input type="email" name="email" placeholder="team@company.com" required />
                  </label>
                  <label className="contact-sales-field">
                    <span>Company</span>
                    <input type="text" name="company" placeholder="Acme Inc." required />
                  </label>
                  <label className="contact-sales-field">
                    <span>Monthly volume</span>
                    <input type="text" name="volume" placeholder="5000 PDFs / month" required />
                  </label>
                </div>
                <label className="contact-sales-field">
                  <span>Requirements</span>
                  <textarea
                    name="requirements"
                    placeholder="Tell us about file sizes, workflows, procurement needs, integrations, or support expectations."
                    rows={6}
                    required
                  />
                </label>
                <div className="contact-sales-copy">
                  Submitting opens your mail client with the prefilled request so your team can send it directly.
                </div>
                <button type="submit" className="btn btn-outline-red btn-lg">Contact Sales</button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}