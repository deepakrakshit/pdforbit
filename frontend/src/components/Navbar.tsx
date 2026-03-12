import { useState, useEffect } from 'react';
import Link from 'next/link';
import { TOOLS } from '@/data/tools';
import { useAuth } from '@/components/AuthProvider';
import { getToolPathById } from '@/lib/seo/routes';
import type { ModalType } from './Modal';

interface NavbarProps {
  onOpenModal: (type: ModalType) => void;
}

export default function Navbar({ onOpenModal }: NavbarProps) {
  const { user, isAuthenticated, logout, isLoading } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setMobileOpen(false);
        document.body.style.overflow = '';
      }
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, []);

  const toggleMobile = () => {
    const next = !mobileOpen;
    setMobileOpen(next);
    document.body.style.overflow = next ? 'hidden' : '';
  };

  const closeMobile = () => {
    setMobileOpen(false);
    document.body.style.overflow = '';
  };

  const handleNav = (path: string) => {
    window.location.assign(path);
    closeMobile();
  };

  const handleLogout = async () => {
    await logout();
    closeMobile();
    window.location.assign('/');
  };

  const mkSvg = (paths: string) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"
      dangerouslySetInnerHTML={{ __html: paths }} />
  );

  const planLabel = user?.is_admin ? 'INTERNAL' : user?.plan_type.toUpperCase();
  const creditLabel = user?.is_admin ? 'Unlimited' : `${user?.credits_remaining}/${user?.credit_limit}`;

  return (
    <>
      <nav id="nav" role="navigation" aria-label="Main navigation">
        <div className="nav-inner">
          <Link href="/" className="nav-logo" aria-label="PdfORBIT Home">
            <div className="nav-logo-mark" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
                <circle cx="12" cy="12" r="3"/>
                <circle cx="12" cy="12" r="8" strokeDasharray="4 3"/>
              </svg>
            </div>
            <span className="nav-logo-text">Pdf<em>ORBIT</em></span>
          </Link>

          <ul className="nav-links" role="list">
            <li><Link className="nav-link" href="/">Home</Link></li>
            <li><Link className="nav-link" href={getToolPathById('merge')}>Merge PDF</Link></li>
            <li><Link className="nav-link" href={getToolPathById('split')}>Split PDF</Link></li>
            <li><Link className="nav-link" href={getToolPathById('compress')}>Compress</Link></li>
            <li className="nav-dropdown">
              <span className="nav-link" tabIndex={0}>
                All Tools
                <svg className="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M6 9l6 6 6-6"/>
                </svg>
              </span>
              <div className="nav-dd">
                <div className="dd-section-title">All 30+ PDF Tools</div>
                {TOOLS.map(t => (
                  <Link key={t.id} className="dd-item" href={getToolPathById(t.id)}>
                    {mkSvg(t.svg)}
                    <span>{t.name}</span>
                  </Link>
                ))}
              </div>
            </li>
          </ul>

          <div className="nav-right">
            <Link href="/pricing" className="btn btn-ghost btn-sm">Pricing</Link>
            {isAuthenticated && user ? (
              <>
                <span className="nav-credits">
                  {planLabel} · {creditLabel}
                </span>
                <Link href="/dashboard" className="btn btn-ghost btn-sm">Dashboard</Link>
                <button className="btn btn-red btn-sm" onClick={() => void handleLogout()}>Log out</button>
              </>
            ) : !isLoading ? (
              <>
                <button className="btn btn-ghost btn-sm" onClick={() => onOpenModal('login')}>Log in</button>
                <button className="btn btn-red btn-sm" onClick={() => onOpenModal('signup')}>Sign up free</button>
              </>
            ) : null}
            <button
              className={`hamburger${mobileOpen ? ' open' : ''}`}
              id="hamburger"
              aria-label="Toggle menu"
              aria-expanded={mobileOpen}
              onClick={toggleMobile}
            >
              <span/><span/><span/>
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile Drawer */}
      <div id="mobile-drawer" className={mobileOpen ? 'open' : ''} role="dialog" aria-label="Mobile navigation" aria-modal="true">
        <div className="mob-section">
          <div className="mob-section-title">Tools</div>
          <div className="mob-tools-grid">
            {TOOLS.slice(0, 12).map(t => (
              <span key={t.id} className="mob-tool-link" onClick={() => handleNav(getToolPathById(t.id))}>
                {mkSvg(t.svg)} {t.name}
              </span>
            ))}
          </div>
        </div>
        <div className="mob-section">
          <div className="mob-section-title">Pages</div>
          <span className="mob-link" onClick={() => handleNav('/pricing')}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8m-4-4v4"/></svg>
            Pricing
          </span>
          <span className="mob-link" onClick={() => handleNav('/faq')}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            FAQ
          </span>
          <span className="mob-link" onClick={() => handleNav('/about')}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            About
          </span>
        </div>
        <div className="mob-section">
          <div className="mob-section-title">Account</div>
          {isAuthenticated && user ? (
            <>
              <span className="mob-link" onClick={() => handleNav('/dashboard')}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 7h10v4H7z"/><path d="M7 15h4"/><path d="M13 15h4"/></svg>
                Dashboard
              </span>
              <div className="mob-account-chip">{planLabel} · {user.is_admin ? 'Unlimited usage' : `${user.credits_remaining}/${user.credit_limit} credits`}</div>
              <span className="mob-link" onClick={() => void handleLogout()}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
                Log out
              </span>
            </>
          ) : (
            <>
              <span className="mob-link" onClick={() => { onOpenModal('login'); closeMobile(); }}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="8" r="4"/><path d="M6 20v-2a4 4 0 014-4h4a4 4 0 014 4v2"/></svg>
                Log in
              </span>
              <span className="mob-link" onClick={() => { onOpenModal('signup'); closeMobile(); }}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></svg>
                Sign up free
              </span>
            </>
          )}
        </div>
      </div>
    </>
  );
}
