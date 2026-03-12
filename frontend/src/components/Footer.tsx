import { useState } from 'react';
import Link from 'next/link';
import { TOOLS } from '@/data/tools';
import { getToolPathById } from '@/lib/seo/routes';

const FEATURED_TOOLS = ['merge', 'split', 'compress', 'pdf2word', 'ocr', 'translate', 'protect', 'watermark'];

export default function Footer() {
  const [launchPad, setLaunchPad] = useState<'app-store' | 'play-store' | null>(null);

  const featuredTools = FEATURED_TOOLS.map(id => TOOLS.find(t => t.id === id)).filter(Boolean) as typeof TOOLS;
  const storeLabel = launchPad === 'app-store' ? 'App Store docking bay' : 'Google Play launch lane';
  const goTo = (path: string) => window.location.assign(path);

  return (
    <>
      <footer>
        <div className="wrap">
          <div className="footer-grid">
            <div>
              <div className="footer-brand">
                <div className="footer-brand-mark">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
                    <circle cx="12" cy="12" r="3"/>
                    <circle cx="12" cy="12" r="8" strokeDasharray="4 3"/>
                  </svg>
                </div>
                <span className="footer-brand-name">Pdf<em>ORBIT</em></span>
              </div>
              <div className="footer-tagline">
                All your PDFs. One orbit.<br/>
                Enterprise-grade PDF processing for everyone. Files auto-deleted after 60 minutes.
              </div>
            </div>

            <div>
              <div className="footer-col-title">PDF Tools</div>
              <div className="footer-links">
                {featuredTools.map(t => (
                  <Link key={t.id} href={getToolPathById(t.id)}>{t.name}</Link>
                ))}
              </div>
            </div>

            <div>
              <div className="footer-col-title">Platform</div>
              <div className="footer-links">
                <Link href="/pricing">Pricing</Link>
                <Link href="/api-docs">API Docs</Link>
                <Link href="/faq">FAQ</Link>
                <Link href="/changelog">Changelog</Link>
                <Link href="/status">Status</Link>
              </div>
            </div>

            <div>
              <div className="footer-col-title">Company</div>
              <div className="footer-links">
                <Link href="/about">About Us</Link>
                <Link href="/contact">Contact</Link>
                <Link href="/enterprise">Enterprise</Link>
                <Link href="/privacy">Privacy Policy</Link>
                <Link href="/terms">Terms of Service</Link>
                <a href="mailto:support@pdforbit.app">support@pdforbit.app</a>
              </div>
            </div>
          </div>
        </div>

        <div className="footer-bottom">
          <div className="wrap">
            <div className="footer-bottom-inner">
              <span className="footer-copy">© 2026 PdfORBIT. All files auto-deleted after 60 minutes. AES-256 encrypted.</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                <div className="footer-stores">
                  <button type="button" className="store-badge" onClick={() => setLaunchPad('app-store')}>
                    <svg viewBox="0 0 24 24" fill="currentColor" width="13" height="13">
                      <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11"/>
                    </svg>
                    App Store
                  </button>
                  <button type="button" className="store-badge" onClick={() => setLaunchPad('play-store')}>
                    <svg viewBox="0 0 24 24" fill="currentColor" width="13" height="13">
                      <path d="M3.18 23.76a2 2 0 001.86-.21l.06-.04 10.4-5.99-2.36-2.37zM.41 1.81C.16 2.11 0 2.57 0 3.16v17.68c0 .59.16 1.05.42 1.35l.07.07 9.9-9.9v-.22zM20.65 10.84l-2.88-1.66-2.69 2.69 2.69 2.69 2.9-1.67c.83-.48.83-1.27-.02-2.05zM5.04.48L15.47 6.49 13.12 8.84z"/>
                    </svg>
                    Google Play
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </footer>

      <div className={`modal-backdrop${launchPad ? ' open' : ''}`} onClick={() => setLaunchPad(null)}>
        <div className="modal orbit-launch-modal" onClick={(event) => event.stopPropagation()}>
          <button type="button" className="modal-close" onClick={() => setLaunchPad(null)} aria-label="Close launch pad notice">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6 6 18M6 6l12 12"/>
            </svg>
          </button>
          <div className="modal-logo">
            <div className="modal-logo-mark">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
                <circle cx="12" cy="12" r="3"/>
                <circle cx="12" cy="12" r="8" strokeDasharray="4 3"/>
              </svg>
            </div>
            <span className="modal-logo-text">Pdf<em>ORBIT</em></span>
          </div>
          <div className="orbit-modal-kicker">// Coming soon</div>
          <h2>{storeLabel}</h2>
          <p className="modal-sub orbit-modal-copy">
            The mobile orbit is still aligning. Native apps are not live yet, but the web platform is fully operational right now.
          </p>
          <div className="orbit-modal-panel">
            <div className="orbit-modal-pill">Launch status: docking in progress</div>
            <p>
              Until the app stores open, you can use PdfORBIT in the browser for uploads, processing, downloads, OCR, translation, and Orbit Brief jobs.
            </p>
          </div>
          <div className="orbit-modal-actions">
            <button type="button" className="btn btn-red btn-lg" onClick={() => { setLaunchPad(null); goTo(getToolPathById('merge')); }}>
              Open a Tool
            </button>
            <button type="button" className="btn btn-ghost btn-lg" onClick={() => { setLaunchPad(null); goTo('/contact'); }}>
              Contact Mission Control
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
