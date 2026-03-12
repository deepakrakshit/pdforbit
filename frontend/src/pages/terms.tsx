import Head from 'next/head';

export default function Terms() {
  return (
    <>
      <Head>
        <title>Terms of Service — PdfORBIT</title>
        <meta name="description" content="PdfORBIT Terms of Service." />
      </Head>
      <div className="static-page">
        <div className="static-hero">
          <div className="wrap">
            <div className="static-hero-inner">
              <div className="tag">// Legal</div>
              <h1>Terms of Service</h1>
              <p>Last updated: March 2026 · By using PdfORBIT you agree to these current service terms.</p>
            </div>
          </div>
        </div>
        <div className="static-body">
          <div className="wrap">
            <div className="prose-section">

              <h2>1. Acceptance of Terms</h2>
              <p>By accessing or using PdfORBIT (&ldquo;the Service&rdquo;), you agree to be bound by these Terms of Service. If you do not agree, do not use the Service.</p>

              <h2>2. Acceptable Use</h2>
              <p>You may use the Service to process PDF files for lawful purposes only. You agree not to:</p>
              <ul style={{ paddingLeft: 24, lineHeight: 2 }}>
                <li>Upload files containing illegal content, malware, or material that infringes third-party intellectual property rights.</li>
                <li>Attempt to reverse engineer, scrape, or circumvent any security measures of the Service.</li>
                <li>Use the Service to process files you do not own or do not have permission to process.</li>
                <li>Use automated tools to abuse free tier limits or degrade service performance for other users.</li>
              </ul>

              <h2>3. Account Responsibility</h2>
              <p>You are responsible for maintaining the confidentiality of your account credentials and for all activity that occurs under your account. Notify us immediately of any unauthorised access.</p>

              <h2>4. Intellectual Property</h2>
              <p>You retain full ownership of all files you upload. We claim no ownership or licence over your content. You grant us a limited licence solely to process your files as part of the Service.</p>
              <p>The PdfORBIT software, brand, interface, and platform materials remain the property of their respective operators and licensors and are protected by applicable intellectual property laws.</p>

              <h2>5. Limitation of Liability</h2>
              <p>THE SERVICE IS PROVIDED &ldquo;AS IS&rdquo; WITHOUT WARRANTIES OF ANY KIND. TO THE MAXIMUM EXTENT PERMITTED BY LAW, PDFORBIT SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING LOSS OF DATA, LOSS OF PROFITS, OR INTERRUPTION OF BUSINESS.</p>
              <p>Our total liability for any claim arising from the Service shall not exceed the amount you paid us in the 12 months preceding the claim.</p>

              <h2>6. Plans, Credits, and Future Billing</h2>
              <p>PdfORBIT may offer free, pro, enterprise, promotional, or internal access tiers. Available features, usage limits, and credits may change over time as the service evolves.</p>
              <p>Public self-serve billing and subscription flows may be introduced later. If paid plans become available, the applicable pricing, renewal terms, and cancellation rules will be presented at the point of purchase.</p>

              <h2>7. Termination</h2>
              <p>We reserve the right to suspend or terminate accounts that violate these terms, abuse service resources, or create security risk for the platform. Temporary files and generated artifacts are already subject to automatic deletion after the standard retention window.</p>

              <h2>8. AI-Assisted Tools</h2>
              <p>Some PdfORBIT tools rely on OCR or external AI providers to produce translations and summaries. AI-generated outputs may contain errors, omissions, or formatting simplifications, and you are responsible for reviewing results before relying on them for legal, financial, or operational decisions.</p>

              <h2>9. Changes to the Service and Terms</h2>
              <p>We may update the Service, these Terms, or product limits as the platform evolves. Continued use of PdfORBIT after updated terms are published constitutes acceptance of those changes.</p>

              <h2>10. Contact</h2>
              <p>Questions about these terms: <a href="mailto:support@pdforbit.app" style={{ color: 'var(--red)' }}>support@pdforbit.app</a></p>

            </div>
          </div>
        </div>
      </div>
    </>
  );
}
