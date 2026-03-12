import Head from 'next/head';
import Link from 'next/link';
import { getToolPathById } from '@/lib/seo/routes';

type ErrorScreenProps = {
  statusCode: number;
  title?: string;
  message?: string;
};

type ErrorCopy = {
  eyebrow: string;
  title: string;
  message: string;
  primaryHref: string;
  primaryLabel: string;
  secondaryHref: string;
  secondaryLabel: string;
};

function getErrorCopy(statusCode: number): ErrorCopy {
  if (statusCode === 404) {
    return {
      eyebrow: 'Navigation fault',
      title: 'This route drifted out of orbit.',
      message: 'The page you requested does not exist, may have moved, or was never published into this sector.',
      primaryHref: '/',
      primaryLabel: 'Return Home',
      secondaryHref: '/faq',
      secondaryLabel: 'Open FAQ',
    };
  }

  if (statusCode === 403) {
    return {
      eyebrow: 'Access denied',
      title: 'Clearance level not high enough.',
      message: 'This area is locked behind permissions. Sign in with the right account or return to a public route.',
      primaryHref: '/login',
      primaryLabel: 'Log In',
      secondaryHref: '/',
      secondaryLabel: 'Back to Home',
    };
  }

  if (statusCode === 401) {
    return {
      eyebrow: 'Authentication required',
      title: 'Session signal lost.',
      message: 'Your request needs an active account session before PdfORBIT can route it any further.',
      primaryHref: '/login',
      primaryLabel: 'Sign In',
      secondaryHref: '/signup',
      secondaryLabel: 'Create Account',
    };
  }

  if (statusCode >= 500) {
    return {
      eyebrow: 'Core failure',
      title: 'The control deck hit turbulence.',
      message: 'Something went wrong on our side while rendering this page. The fastest path is to retry or jump back to a stable route.',
      primaryHref: '/',
      primaryLabel: 'Stabilize Home',
      secondaryHref: getToolPathById('merge'),
      secondaryLabel: 'Open a Tool',
    };
  }

  return {
    eyebrow: 'Request interrupted',
    title: 'This response did not land cleanly.',
    message: 'PdfORBIT received the request but could not render this page in a usable state.',
    primaryHref: '/',
    primaryLabel: 'Go Home',
    secondaryHref: '/faq',
    secondaryLabel: 'Help Center',
  };
}

export default function ErrorScreen({ statusCode, title, message }: ErrorScreenProps) {
  const content = getErrorCopy(statusCode);

  return (
    <>
      <Head>
        <title>{statusCode} | PdfORBIT</title>
        <meta name="description" content={message || content.message} />
        <meta name="robots" content="noindex,follow" />
      </Head>

      <main className="error-scene">
        <div className="error-ambient error-ambient-a" aria-hidden="true" />
        <div className="error-ambient error-ambient-b" aria-hidden="true" />
        <div className="error-grid" aria-hidden="true" />

        <section className="error-shell wrap-lg">
          <div className="error-panel">
            <div className="error-panel-copy">
              <div className="error-kicker">// {content.eyebrow}</div>
              <div className="error-status t-display">{statusCode}</div>
              <h1 className="error-title">{title || content.title}</h1>
              <p className="error-text">{message || content.message}</p>

              <div className="error-actions">
                <Link className="btn btn-red btn-lg" href={content.primaryHref}>
                  {content.primaryLabel}
                </Link>
                <Link className="btn btn-ghost btn-lg" href={content.secondaryHref}>
                  {content.secondaryLabel}
                </Link>
              </div>
            </div>

            <div className="error-panel-visual" aria-hidden="true">
              <div className="error-orbit-ring error-orbit-ring-outer" />
              <div className="error-orbit-ring error-orbit-ring-mid" />
              <div className="error-orbit-ring error-orbit-ring-inner" />
              <div className="error-core">
                <span className="error-core-label">PdfORBIT</span>
                <span className="error-core-sub">status {statusCode}</span>
              </div>
              <div className="error-node error-node-a" />
              <div className="error-node error-node-b" />
              <div className="error-node error-node-c" />
              <div className="error-node error-node-d" />
            </div>
          </div>

          <div className="error-readouts">
            <div className="error-readout">
              <span className="error-readout-label">Route status</span>
              <span className="error-readout-value">{statusCode}</span>
            </div>
            <div className="error-readout">
              <span className="error-readout-label">Suggested recovery</span>
              <span className="error-readout-value">Retry navigation</span>
            </div>
            <div className="error-readout">
              <span className="error-readout-label">Fallback routes</span>
              <span className="error-readout-value">Home / Tools / FAQ</span>
            </div>
          </div>
        </section>
      </main>
    </>
  );
}