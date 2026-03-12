import Head from 'next/head';

export default function Privacy() {
  return (
    <>
      <Head>
        <title>Privacy Policy — PdfORBIT</title>
        <meta name="description" content="PdfORBIT Privacy Policy — how we handle your data." />
      </Head>
      <div className="static-page">
        <div className="static-hero">
          <div className="wrap">
            <div className="static-hero-inner">
              <div className="tag">// Legal</div>
              <h1>Privacy Policy</h1>
              <p>Last updated: March 2026 · Effective immediately</p>
            </div>
          </div>
        </div>
        <div className="static-body">
          <div className="wrap">
            <div className="prose-section">

              <p>
                PdfORBIT is designed for temporary document processing. Files are uploaded,
                processed, and made available for download, after which they are automatically
                removed from the system. The current production retention target is 60 minutes,
                and PdfORBIT is not intended to function as long-term file storage.
              </p>

              <h2>1. Information We Collect</h2>
              <p>
                <strong>Files you upload.</strong> Files submitted to PdfORBIT are used
                solely to perform the document operation you request (such as converting,
                merging, compressing, or editing). Uploaded files are processed
                temporarily and are not intended to be stored permanently on our systems.
              </p>

              <p>
                <strong>Account information.</strong> If account features are enabled,
                we may collect basic account information such as an email address and
                authentication credentials required to provide access to the service,
                maintain job history, and enforce usage limits.
              </p>

              <p>
                <strong>Technical and usage information.</strong> We may collect limited
                technical information such as browser type, device type, and basic usage
                statistics to help maintain and improve the service. This information is
                used in aggregated form and is not intended to identify individual users.
              </p>

              <p>
                <strong>AI processing inputs.</strong> When you use AI-assisted tools such as
                translation or Orbit Brief summarization, extracted text from your document may
                be sent to the configured AI provider in order to generate the requested output.
              </p>


              <h2>2. How We Use Your Data</h2>
              <p>
                Information collected through PdfORBIT is used exclusively to operate
                and improve the platform. This includes processing uploaded files,
                delivering results, maintaining system reliability, and providing
                support when requested.
              </p>

              <p>
                We do not sell, rent, or trade user data to third parties. Uploaded
                files are not used for advertising, marketing analysis, or training
                external systems.
              </p>

              <p>
                For AI-assisted tools, extracted text is transmitted only to the provider
                needed to complete the requested job. Those requests are made solely to
                return your translation or summary result.
              </p>


              <h2>3. File Processing and Retention</h2>
              <p>
                Files uploaded to PdfORBIT are processed temporarily in order to perform
                the selected document operation. After processing is complete, files
                remain available for download for a limited time before being automatically
                removed from the system. The current standard retention window is 60 minutes.
              </p>

              <p>
                Because files are processed temporarily, users should download their
                processed results promptly after completion.
              </p>


              <h2>4. Data Security</h2>
              <p>
                We take reasonable technical and organizational measures to protect
                uploaded files and account information from unauthorized access,
                disclosure, or misuse. This includes the use of secure network
                communication and controlled access to processing infrastructure.
              </p>

              <p>
                While we strive to protect user data, no internet-based system can be
                guaranteed to be completely secure.
              </p>

              <p>
                Security controls may include HTTPS transport, signed result URLs, temporary
                storage policies, access controls for service infrastructure, and monitoring
                designed to keep the platform operational and abuse-resistant.
              </p>


              <h2>5. Your Rights</h2>
              <p>
                Depending on your jurisdiction, you may have rights regarding access,
                correction, or deletion of personal data associated with your account.
                Requests related to personal data can be submitted using the contact
                information below.
              </p>


              <h2>6. Cookies</h2>
              <p>
                PdfORBIT may use essential cookies or local session mechanisms required for
                core functionality such as authentication, request continuity, and basic site
                operation. We do not use advertising cookies.
              </p>


              <h2>7. Changes to This Policy</h2>
              <p>
                This Privacy Policy may be updated periodically to reflect changes in
                the service or applicable regulations. When updates are made, the
                "Last updated" date at the top of this page will be revised.
              </p>


              <h2>8. Contact</h2>
              <p>
                If you have questions regarding this Privacy Policy or data handling
                practices, please contact us at{' '}
                <a href="mailto:support@pdforbit.app" style={{ color: 'var(--red)' }}>
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
