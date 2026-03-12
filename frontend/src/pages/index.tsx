import Head from 'next/head';
import { useState } from 'react';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/router';
import { TOOLS } from '@/data/tools';
import { CATS } from '@/data/categories';
import { FAQ_ITEMS } from '@/data/faq';
import ToolCard from '@/components/ToolCard';
import type { ModalType } from '@/components/Modal';

// Dynamically import Three.js component to avoid SSR issues
const HeroOrbit = dynamic(() => import('@/components/HeroOrbit'), { ssr: false });

interface HomeProps {
  onOpenModal: (type: ModalType) => void;
}

function FaqItem({ q, a, index }: { q: string; a: string; index: number }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`faq-item${open ? ' open' : ''}`}>
      <div className="faq-q" onClick={() => setOpen(!open)}>
        <span className="faq-q-text">{q}</span>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M6 9l6 6 6-6"/>
        </svg>
      </div>
      <div className="faq-a">{a}</div>
    </div>
  );
}

export default function Home({ onOpenModal }: HomeProps) {
  const router = useRouter();
  const [activeCat, setActiveCat] = useState('all');

  const filteredTools = activeCat === 'all' ? TOOLS : TOOLS.filter(t => t.cat === activeCat);

  const scrollToTools = () => {
    document.getElementById('cats-section')?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <>
      <Head>
  <title>PdfORBIT — All Your PDFs. One Orbit.</title>
  <meta
    name="description"
    content="Process, convert, compress, and transform PDF documents instantly in your browser with PdfORBIT."
  />
</Head>
      <div id="page-home">

        {/* HERO */}
        <section className="hero-section">
          <HeroOrbit />
          <div className="h-vignette"/>
          <div className="h-atmos-b"/>
          <div className="h-atmos-t"/>
          <div className="h-scanlines"/>
          <div className="fc tl"/><div className="fc tr"/>
          <div className="fc bl"/><div className="fc br"/>

          <div className="hud-right">
            <div className="hud-item" id="h0"><div className="hud-dot"/><span className="hud-label">OCR Recognition</span></div>
            <div className="hud-item" id="h1"><div className="hud-dot"/><span className="hud-label">Smart Compress</span></div>
            <div className="hud-item" id="h2"><div className="hud-dot"/><span className="hud-label">Merge &amp; Split</span></div>
            <div className="hud-item" id="h3"><div className="hud-dot"/><span className="hud-label">Format Convert</span></div>
            <div className="hud-item" id="h4"><div className="hud-dot"/><span className="hud-label">Encrypt &amp; Sign</span></div>
          </div>

          <div className="h-counter" id="hero-counter">
            <div className="counter-pct" id="ctr-num">0%</div>
            <div className="counter-sub">Processing</div>
          </div>

          <div className="chip" id="chip-in">
            <div className="chip-dot"/>
            <span>report_q4_2025.pdf &nbsp;·&nbsp; 4.2 MB</span>
          </div>
          <div className="chip" id="chip-out">
            <div className="chip-dot"/>
            <span>report_optimized.pdf &nbsp;·&nbsp; 0.8 MB</span>
          </div>

          <div className="hero-content">
            <p className="hero-eyebrow">The Future of Document Processing</p>
            <h1 className="hero-h1">All Your <span className="acc">PDFs.</span><br/>One <span className="acc">Orbit.</span></h1>
            <p className="hero-sub">Upload &nbsp;·&nbsp; Process &nbsp;·&nbsp; Transform &nbsp;·&nbsp; Download</p>
            <div className="hero-cta-row">
              <button className="btn btn-red btn-lg" onClick={scrollToTools}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <polygon points="5 3 19 12 5 21 5 3"/>
                </svg>
                Explore All Tools
              </button>
              <button className="btn btn-ghost btn-lg" onClick={() => router.push('/pricing')}>View Pricing</button>
            </div>
          </div>
        </section>

        {/* Stats bar — outside hero so it never overlaps CTA buttons */}
        <div className="hero-stats">
          <div className="hero-stat"><div className="hero-stat-n">30+</div><div className="hero-stat-l">PDF Tools</div></div>
          <div className="hero-stat"><div className="hero-stat-n">100%</div><div className="hero-stat-l">Free Tier</div></div>
          <div className="hero-stat"><div className="hero-stat-n">Secure</div><div className="hero-stat-l">File Transfer</div></div>
          <div className="hero-stat"><div className="hero-stat-n">Instant</div><div className="hero-stat-l">Processing</div></div>
          <div className="hero-stat"><div className="hero-stat-n">Online</div><div className="hero-stat-l">No Install</div></div>
        </div>

        {/* Tools Section */}
        <div id="cats-section">
          <div className="cats-bar" role="navigation" aria-label="Tool categories">
            <div className="cats-inner" role="tablist">
              {CATS.map(c => (
                <button
                  key={c.id}
                  className={`cat-btn${c.id === activeCat ? ' active' : ''}`}
                  role="tab"
                  aria-selected={c.id === activeCat}
                  onClick={() => setActiveCat(c.id)}
                >
                  {c.label}
                </button>
              ))}
            </div>
          </div>
          <section className="tools-section">
            <div className="wrap">
              <div className="tools-grid" role="list">
                {filteredTools.map(tool => (
                  <ToolCard key={tool.id} tool={tool} />
                ))}
              </div>
            </div>
          </section>
        </div>

        {/* How It Works */}
        <section className="process-section">
          <div className="wrap">
            <div className="section-title">
              <div className="eyebrow">// How it works</div>
              <h2>Four Steps to Done</h2>
              <p>From upload to download in under 60 seconds for most jobs, with secure account-based processing and temporary file retention.</p>
            </div>
            <div className="process-steps">
              <div className="process-step">
                <div className="step-num active">01</div>
                <h4>Select Your Tool</h4>
                <p>Choose from 30+ professional PDF tools, organized by category for quick access.</p>
              </div>
              <div className="process-step">
                <div className="step-num">02</div>
                <h4>Upload Your File</h4>
                <p>Drop your file into the upload zone and start processing instantly using our browser-based tools.</p>
              </div>
              <div className="process-step">
                <div className="step-num">03</div>
                <h4>Configure &amp; Process</h4>
                <p>Configure your options and start processing. The platform handles the document transformation automatically.</p>
              </div>
              <div className="process-step">
                <div className="step-num">04</div>
                <h4>Download &amp; Done</h4>
                <p>Download your processed file as soon as the task completes.</p>
              </div>
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="work-section">
          <div className="wrap">
            <div className="section-title">
              <div className="eyebrow">// Built for every workflow</div>
              <h2>Enterprise-Ready Platform</h2>
              <p>Whether you&apos;re a solo user, a development team, or a global enterprise, PdfORBIT scales with you.</p>
            </div>
            <div className="work-grid">
              <div className="work-cell">
                <div className="work-cell-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                    <rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8m-4-4v4"/>
                  </svg>
                </div>
                <h3>Powerful Web App</h3>
                <p>Access all 30+ PDF tools directly in your browser — zero installation, zero friction, instant results.</p>
                <span className="work-cell-link" onClick={scrollToTools}>
                  Try it now
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14m-7-7l7 7-7 7"/></svg>
                </span>
              </div>
              <div className="work-cell">
                <div className="work-cell-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                    <rect x="5" y="2" width="14" height="20" rx="2"/><line x1="12" y1="18" x2="12.01" y2="18"/>
                  </svg>
                </div>
                <h3>Fully Responsive</h3>
                <p>Optimised for every screen — process documents from your phone, tablet, or desktop, anywhere.</p>
                <span className="work-cell-link">
                  Works on mobile
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14m-7-7l7 7-7 7"/></svg>
                </span>
              </div>
              <div className="work-cell">
                <div className="work-cell-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                    <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/>
                    <path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/>
                  </svg>
                </div>
                <h3>Built for Business</h3>
                <p>Designed to scale from individual users to teams with higher processing limits and advanced workflows.</p>
                <span className="work-cell-link" onClick={() => router.push('/pricing')}>
                  See plans
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14m-7-7l7 7-7 7"/></svg>
                </span>
              </div>
              <div className="work-cell">
                <div className="work-cell-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                    <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
                  </svg>
                </div>
                <h3>Developer Integrations</h3>
                <p>
                Developer tools and automation features are planned to allow applications
                and workflows to integrate document processing directly into their systems.
                </p>
                <span className="work-cell-link">
                  Coming soon
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M5 12h14m-7-7l7 7-7 7"/>
                  </svg>
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* Security Strip */}
        <section style={{ padding: '48px 0', background: 'var(--surface)', borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)' }}>
          <div className="wrap">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 48, flexWrap: 'wrap' }}>
              {[
                { icon: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>', title: 'Secure Processing', sub: 'Files handled temporarily' },
                { icon: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>', title: 'Fast Results', sub: 'Optimized processing engine' },
                { icon: '<path d="M1 6s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1v14s1-1 4-1 5 2 8 2 4-1 4-1"/>', title: 'Online Platform', sub: 'No installation required' },
                { icon: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/>', title: 'Cross-Device', sub: 'Desktop, tablet, mobile' },
                { icon: '<polyline points="20 6 9 17 4 12"/>', title: 'Privacy Focused', sub: 'Files used only for processing' },
              ].map(item => (
                <div key={item.title} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <svg viewBox="0 0 24 24" fill="none" stroke="var(--red)" strokeWidth="1.6" width="24" height="24" dangerouslySetInnerHTML={{ __html: item.icon }}/>
                  <div>
                    <div style={{ fontFamily: 'var(--font-display)', fontSize: 13, letterSpacing: 1, textTransform: 'uppercase' }}>{item.title}</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--muted)', letterSpacing: 1, marginTop: 3 }}>{item.sub}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Premium CTA */}
        <section className="premium-section">
          <div className="wrap">
            <div className="premium-inner">
              <div className="premium-badge">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="13" height="13">
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                </svg>
                Premium Plan
              </div>
              <h2>Get More with <span style={{ color: 'var(--red)' }}>Premium</span></h2>
              <p>Unlock higher processing limits, faster performance, and advanced document tools.</p>
              <div className="premium-features">
                {['Higher file limits', 'Priority processing', 'Batch tools', 'Advanced features', 'Extended download window'].map(f => (
                  <div key={f} className="premium-feat">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <polyline points="20 6 9 17 4 12"/>
                    </svg>
                    {f}
                  </div>
                ))}
              </div>
              <button className="btn btn-red btn-lg" onClick={() => router.push('/pricing')}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                </svg>
                Get Premium — from $9/mo
              </button>
            </div>
          </div>
        </section>

        {/* FAQ Preview */}
        <section style={{ padding: '80px 0', borderTop: '1px solid var(--border)' }}>
          <div className="wrap">
            <div className="section-title">
              <div className="eyebrow">// FAQ</div>
              <h2>Common Questions</h2>
            </div>
            <div className="faq-list">
              {FAQ_ITEMS.slice(0, 4).map((item, i) => (
                <FaqItem key={i} q={item.q} a={item.a} index={i} />
              ))}
            </div>
            <div style={{ textAlign: 'center', marginTop: 32 }}>
              <button className="btn btn-ghost" onClick={() => router.push('/faq')}>
                View all FAQs
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14">
                  <path d="M5 12h14m-7-7l7 7-7 7"/>
                </svg>
              </button>
            </div>
          </div>
        </section>

      </div>
    </>
  );
}