import React, { useEffect, useRef, useState } from 'react';
import Head from 'next/head';
import PricingPlans from '@/components/PricingPlans';
import { getEnterpriseContactUrl } from '@/lib/razorpay';
import type { ModalType } from '@/components/Modal';

interface PricingProps {
  onOpenModal: (type: ModalType) => void;
}

const Check = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2.5" width="15" height="15" style={{ flexShrink: 0 }}>
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

const Xmark = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="15" height="15" style={{ flexShrink: 0, color: 'var(--muted)' }}>
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

const PlannedBadge = () => <span className="tbl-planned">Planned</span>;

type Period = 'monthly' | 'yearly';

type Cell = React.ReactNode;
type Row = {
  label: string;
  category?: boolean;
  free?: Cell;
  pro?: Cell;
  enterprise?: Cell;
};

const PLANS = [
  {
    id: 'free',
    tier: '01',
    name: 'Free',
    tagline: 'Perfect for occasional use',
    monthlyPrice: 0,
    yearlyPrice: 0,
    features: [
      { label: 'All 30+ PDF tools', ok: true },
      { label: 'Up to 50 MB as guest', ok: true },
      { label: '30 daily credits on accounts', ok: true },
      { label: 'Temporary file processing', ok: true },
      { label: 'Secure file transfer', ok: true },
      { label: '60-minute auto-delete policy', ok: true },
      { label: 'Signed download links', ok: true },
      { label: 'No subscription required', ok: true },
      { label: 'Developer integrations', ok: false },
    ],
    cta: 'Start for free',
    ctaVariant: 'ghost' as const,
    featured: false,
    badge: null as string | null,
  },
  {
    id: 'pro',
    tier: '02',
    name: 'Pro',
    tagline: 'Verified Pro access with higher daily credits',
    monthlyPrice: 500,
    yearlyPrice: 200,
    features: [
      { label: 'Everything in Free', ok: true },
      { label: '1000 daily credits', ok: true },
      { label: 'Monthly or yearly Razorpay billing', ok: true },
      { label: 'Server-side payment verification', ok: true },
      { label: 'Account upgraded after verified payment', ok: true },
      { label: 'Active subscription tracking', ok: true },
      { label: '60-minute auto-delete policy', ok: true },
      { label: 'Developer integrations (planned)', ok: true },
    ],
    cta: 'Get Pro',
    ctaVariant: 'red' as const,
    featured: true,
    badge: 'Most Popular',
  },
  {
    id: 'enterprise',
    tier: '03',
    name: 'Enterprise',
    tagline: 'Custom solutions at scale',
    monthlyPrice: null as number | null,
    yearlyPrice: null as number | null,
    features: [
      { label: 'Everything in Pro', ok: true },
      { label: 'Higher file size limits', ok: true },
      { label: 'Custom retention policy', ok: true },
      { label: 'Custom infrastructure allocation', ok: true },
      { label: 'Advanced team features', ok: true },
      { label: 'Usage analytics', ok: true },
      { label: 'Custom integrations', ok: true },
      { label: 'Priority technical support', ok: true },
    ],
    cta: 'Contact Sales',
    ctaVariant: 'outline' as const,
    featured: false,
    badge: null,
  },
];

const TABLE: Row[] = [
  { label: 'ACCESS & BILLING', category: true },
  { label: 'PDF tools available', free: '30+', pro: '30+', enterprise: '30+' },
  { label: 'Daily credits', free: '30', pro: '1000', enterprise: 'Custom' },
  { label: 'Billing model', free: 'No subscription', pro: 'Razorpay monthly or yearly', enterprise: 'Contact sales' },
  { label: 'Account plan state', free: 'Free', pro: 'Verified Pro subscription', enterprise: 'Sales-managed' },

  { label: 'FILES & PRIVACY', category: true },
  { label: 'Current upload limit', free: '50 MB guest / 250 MB signed in', pro: '250 MB signed in', enterprise: 'Custom review' },
  { label: 'File retention', free: '60 minutes', pro: '60 minutes', enterprise: 'Custom review' },
  { label: 'Secure file transfer', free: <Check />, pro: <Check />, enterprise: <Check /> },
  { label: 'Temporary file processing', free: <Check />, pro: <Check />, enterprise: <Check /> },
  { label: 'Signed download links', free: <Check />, pro: <Check />, enterprise: <Check /> },
  { label: 'Privacy-focused design', free: <Check />, pro: <Check />, enterprise: <Check /> },

  { label: 'ROADMAP & ENTERPRISE', category: true },
  { label: 'Developer integrations', free: <Xmark />, pro: <PlannedBadge />, enterprise: <PlannedBadge /> },
  { label: 'Team access controls', free: <Xmark />, pro: <Xmark />, enterprise: <PlannedBadge /> },
  { label: 'Custom integrations', free: <Xmark />, pro: <Xmark />, enterprise: <PlannedBadge /> },
  { label: 'Usage analytics', free: <Xmark />, pro: <Xmark />, enterprise: <PlannedBadge /> },
  { label: 'Custom infrastructure', free: <Xmark />, pro: <Xmark />, enterprise: <PlannedBadge /> },

  { label: 'SUPPORT', category: true },
  { label: 'Support path', free: 'Email/contact', pro: 'Email/contact', enterprise: 'Sales-led' },
  { label: 'Cancellation path', free: 'Not applicable', pro: 'Subscription state + support', enterprise: 'Contract-specific' },
  { label: 'Onboarding assistance', free: <Xmark />, pro: <Xmark />, enterprise: <PlannedBadge /> },
];

const FAQ_DATA = [
  {
    section: 'General',
    items: [
      {
        q: 'What do I get with the Free Plan?',
        a: 'The current public platform focuses on secure account-based PDF processing, temporary storage, and access to the current tool catalog. Plan labels describe product direction, but the live service still runs with a shared 60-minute auto-delete policy.',
      },
      {
        q: 'Why should I upgrade to Pro?',
        a: 'Pro is live for users who need 1000 daily credits and a verified subscription state on their account. Enterprise remains the route for custom requirements that are not self-serve today.',
      },
      {
        q: 'Can I switch plans if my needs change?',
        a: 'Plan packaging is still evolving. If you need a different tier or higher usage limits, contact the team so they can advise you on the current rollout status.',
      },
    ],
  },
  {
    section: 'Billing',
    items: [
      {
        q: 'Can I use centralized billing for a team?',
        a: 'Centralized billing and team purchasing are being prepared for enterprise customers. If your organization needs multi-user access or procurement support, use the Enterprise or Contact pages to reach the team.',
      },
      {
        q: 'What payment methods do you accept?',
        a: 'Self-serve Pro checkout is live through Razorpay. The exact set of payment methods depends on what Razorpay makes available for your checkout session and region.',
      },
      {
        q: 'What happens if I change plans mid-cycle?',
        a: 'Plan migration between self-serve tiers is not automated yet. If you need a billing change outside the current monthly or yearly Pro options, contact the team before making another purchase.',
      },
      {
        q: 'Will I receive a tax invoice?',
        a: 'Enterprise billing conversations can be handled directly with the team. If you need invoice or tax-document confirmation for self-serve checkout, contact support after payment.',
      },
    ],
  },
  {
    section: 'Privacy & Security',
    items: [
      {
        q: 'Is my data safe with PdfORBIT?',
        a: 'Privacy is a core principle, not an afterthought. Uploaded files are processed temporarily, download results are exposed through signed links, and files are scheduled for deletion after 60 minutes rather than retained indefinitely.',
      },
      {
        q: 'Will PdfORBIT work for my industry or workflow?',
        a: 'PdfORBIT is built for broad PDF workflows including conversion, OCR, organization, repair, security, and AI-assisted document tasks. If you need stricter controls, scale, or support expectations, the Enterprise page outlines the intended direction for organizations.',
      },
    ],
  },
];

function AnimatedCounter({ end, suffix = '', duration = 1800 }: { end: number; suffix?: string; duration?: number }) {
  const [val, setVal] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const obs = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) {
        return;
      }

      obs.disconnect();
      const start = performance.now();

      const tick = (now: number) => {
        const t = Math.min((now - start) / duration, 1);
        const ease = 1 - Math.pow(1 - t, 3);
        setVal(Math.round(ease * end));
        if (t < 1) {
          requestAnimationFrame(tick);
        }
      };

      requestAnimationFrame(tick);
    }, { threshold: 0.3 });

    if (ref.current) {
      obs.observe(ref.current);
    }

    return () => obs.disconnect();
  }, [duration, end]);

  return (
    <span ref={ref}>
      {val.toLocaleString('en-IN')}
      {suffix}
    </span>
  );
}

function FaqItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);

  return (
    <div className={`pfaq-item${open ? ' open' : ''}`} onClick={() => setOpen((value) => !value)}>
      <div className="pfaq-q">
        <span>{q}</span>
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          width="14"
          height="14"
          style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform .2s', flexShrink: 0 }}
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </div>
      <div className={`pfaq-body${open ? ' open' : ''}`}>
        <div className="pfaq-a">{a}</div>
      </div>
    </div>
  );
}

export default function Pricing({ onOpenModal }: PricingProps) {
  const [period, setPeriod] = useState<Period>('yearly');
  const [showTable, setShowTable] = useState(false);
  const [tableVisible, setTableVis] = useState(false);
  const [faqSection, setFaqSection] = useState(0);
  const [showCheckoutModal, setShowCheckoutModal] = useState(false);
  const tableWrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (showTable) {
      requestAnimationFrame(() => requestAnimationFrame(() => setTableVis(true)));
      setTimeout(() => {
        tableWrapRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }, 80);
    } else {
      setTableVis(false);
    }
  }, [showTable]);

  const getPrice = (plan: typeof PLANS[number]) => {
    if (plan.monthlyPrice === null) {
      return null;
    }
    return period === 'yearly' ? plan.yearlyPrice : plan.monthlyPrice;
  };

  const getPeriodLine = (plan: typeof PLANS[number]) => {
    if (plan.id === 'free') {
      return 'Forever free · no card required';
    }
    if (plan.id === 'enterprise') {
      return 'Volume pricing · annual contract';
    }
    if (period === 'yearly') {
      return 'per month · billed ₹2,400 / year';
    }
    return 'per month · billed monthly';
  };

  const proSavingYear = (PLANS[1].monthlyPrice! - PLANS[1].yearlyPrice!) * 12;

  return (
    <>
      <Head>
        <title>Pricing — PdfORBIT</title>
        <meta name="description" content="Simple, transparent pricing for PdfORBIT. Start free, upgrade when you need more." />
      </Head>

      <div className="static-page pricing-page">
        <div className="pricing-hero">
          <div className="pricing-hero-grid-bg" />
          <div className="wrap">
            <div className="pricing-hero-inner">
              <div className="pricing-hero-eyebrow">
                <div className="pricing-hero-dot" />
                <span>// PRICING</span>
              </div>
              <h1 className="pricing-hero-h1">
                Plans Built for
                <br />
                <span className="pricing-hero-acc">Every Workflow</span>
              </h1>
              <p className="pricing-hero-sub">
                Start free and process documents in seconds. Upgrade for higher daily credits,
                <br />
                verified Pro status, and secure Razorpay billing. No hidden fees.
              </p>
            </div>
          </div>
        </div>

        <div className="pricing-proof-bar">
          <div className="wrap">
            <div className="pricing-proof-inner">
              <div className="pricing-proof-stat">
                <span className="pricing-proof-n"><AnimatedCounter end={50000} suffix="+" /></span>
                <span className="pricing-proof-l">Documents Processed</span>
              </div>
              <div className="pricing-proof-divider" />
              <div className="pricing-proof-stat">
                <span className="pricing-proof-n"><AnimatedCounter end={8500} suffix="+" /></span>
                <span className="pricing-proof-l">Active Users</span>
              </div>
              <div className="pricing-proof-divider" />
              <div className="pricing-proof-stat">
                <span className="pricing-proof-n">30+</span>
                <span className="pricing-proof-l">PDF Tools</span>
              </div>
              <div className="pricing-proof-divider" />
              <div className="pricing-proof-stat">
                <span className="pricing-proof-n"><AnimatedCounter end={99} suffix="%" /></span>
                <span className="pricing-proof-l">Uptime</span>
              </div>
            </div>
          </div>
        </div>

        <div className="static-body" style={{ paddingTop: 56 }}>
          <div className="wrap">
            <div className="ptoggle-outer">
              <div className="ptoggle-wrap">
                <button className={`ptoggle-btn${period === 'monthly' ? ' active' : ''}`} onClick={() => setPeriod('monthly')}>
                  Monthly
                </button>
                <button className={`ptoggle-btn${period === 'yearly' ? ' active' : ''}`} onClick={() => setPeriod('yearly')}>
                  Yearly
                  <span className="ptoggle-pill">Save 60%</span>
                </button>
              </div>
              {period === 'monthly' ? (
                <div className="ptoggle-hint">
                  <svg viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2" width="12" height="12">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  Switch to yearly and save ₹{proSavingYear.toLocaleString('en-IN')} on Pro
                </div>
              ) : null}
            </div>

            <div className="pricing-grid">
              {PLANS.map((plan) => {
                const price = getPrice(plan);
                const isYearly = period === 'yearly';

                return (
                  <div key={plan.id} className={`pricing-card${plan.featured ? ' featured' : ''}`}>
                    <div className="pc-corner-tl" />
                    <div className="pc-corner-br" />

                    {plan.badge ? <div className="pricing-badge">{plan.badge}</div> : null}

                    <div className="pc-tier">{plan.tier}</div>
                    <div className="pc-name">{plan.name}</div>
                    <div className="pc-tagline">{plan.tagline}</div>

                    <div className="pc-price-block">
                      {price === null ? (
                        <div className="pc-price-custom">Custom</div>
                      ) : price === 0 ? (
                        <div className="pc-price-free">Free</div>
                      ) : (
                        <div className="pc-price-row">
                          <div className="pc-price">
                            <sup>₹</sup>
                            <span>{price.toLocaleString('en-IN')}</span>
                          </div>
                          {isYearly && plan.id === 'pro' ? (
                            <div className="pc-price-was">
                              <span className="pc-price-strike">₹{plan.monthlyPrice!.toLocaleString('en-IN')}</span>
                              <span className="pc-price-save">/ mo</span>
                            </div>
                          ) : null}
                        </div>
                      )}
                      <div className="pc-period">{getPeriodLine(plan)}</div>
                    </div>

                    <div className="pc-divider" />

                    <ul className="pc-features">
                      {plan.features.map((feature) => (
                        <li key={feature.label} className={`pc-feat${!feature.ok ? ' no' : ''}`}>
                          {feature.ok ? <Check /> : <Xmark />}
                          <span>{feature.label}</span>
                        </li>
                      ))}
                    </ul>

                    {plan.ctaVariant === 'ghost' ? (
                      <button className="btn btn-ghost pricing-cta" onClick={() => onOpenModal('signup')}>
                        {plan.cta}
                      </button>
                    ) : null}
                    {plan.ctaVariant === 'red' ? (
                      <button className="btn btn-red btn-lg pricing-cta" onClick={() => setShowCheckoutModal(true)}>
                        {plan.cta}
                      </button>
                    ) : null}
                    {plan.ctaVariant === 'outline' ? (
                      <button className="btn btn-outline-red btn-lg pricing-cta" onClick={() => window.location.assign(getEnterpriseContactUrl())}>
                        {plan.cta}
                      </button>
                    ) : null}
                  </div>
                );
              })}
            </div>

            <div className="pricing-trust-bar">
              {[
                '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
                '<polyline points="20 6 9 17 4 12"/>',
                '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
                '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/>',
              ].map((path, i) => {
                const labels = ['Free plan needs no card', 'Server-verified checkout', 'Files auto-deleted', 'Secure file processing'];
                return (
                  <React.Fragment key={labels[i]}>
                    {i > 0 ? <div className="pricing-trust-sep" /> : null}
                    <div className="pricing-trust-item">
                      <svg viewBox="0 0 24 24" fill="none" stroke="var(--red)" strokeWidth="1.8" width="14" height="14" dangerouslySetInnerHTML={{ __html: path }} />
                      <span>{labels[i]}</span>
                    </div>
                  </React.Fragment>
                );
              })}
            </div>

            <div className="pf-highlights">
              <div className="pf-hl-label">// Why PdfORBIT</div>
              <div className="pf-hl-grid">
                {[
                  {
                    icon: '<path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>',
                    title: 'Self-Serve Processing',
                    desc: 'Start with the current public tool catalog immediately, then upgrade to Pro when you need higher daily credit limits.',
                  },
                  {
                    icon: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/>',
                    title: 'Privacy by Default',
                    desc: 'Files are processed in isolated sessions and permanently deleted. We never store or analyse your documents.',
                  },
                  {
                    icon: '<path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/>',
                    title: 'Enterprise Path',
                    desc: 'Enterprise stays sales-led for organizations that need custom infrastructure, procurement, or rollout support beyond the self-serve plans.',
                  },
                  {
                    icon: '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
                    title: 'Reliable Uptime',
                    desc: '99%+ uptime target. Isolated worker architecture means one heavy job never affects another user.',
                  },
                ].map((item) => (
                  <div key={item.title} className="pf-hl-card">
                    <div className="pf-hl-icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="var(--red)" strokeWidth="1.6" width="20" height="20" dangerouslySetInnerHTML={{ __html: item.icon }} />
                    </div>
                    <div className="pf-hl-title">{item.title}</div>
                    <div className="pf-hl-desc">{item.desc}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="pricing-all-include">
              <div className="pricing-all-label">// Included in every plan</div>
              <div className="pricing-all-items">
                {[
                  { path: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>', label: 'Secure file transfer' },
                  { path: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>', label: 'Temporary file processing' },
                  { path: '<path d="M1 6s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1v14s1-1 4-1 5 2 8 2 4-1 4-1"/>', label: 'Privacy-focused design' },
                  { path: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/>', label: 'Auto file deletion' },
                  { path: '<polyline points="20 6 9 17 4 12"/>', label: 'Signed download links' },
                ].map((item) => (
                  <div key={item.label} className="pricing-all-item">
                    <svg viewBox="0 0 24 24" fill="none" stroke="var(--red)" strokeWidth="1.8" width="15" height="15" dangerouslySetInnerHTML={{ __html: item.path }} />
                    <span>{item.label}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className={`pricing-compare-trigger${showTable ? ' open' : ''}`} onClick={() => setShowTable((value) => !value)}>
              <div className="pct-inner">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" width="16" height="16">
                  <rect x="3" y="3" width="7" height="7" />
                  <rect x="14" y="3" width="7" height="7" />
                  <rect x="3" y="14" width="7" height="7" />
                  <rect x="14" y="14" width="7" height="7" />
                </svg>
                <span>{showTable ? 'Hide' : 'Compare'} all features</span>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14" style={{ transform: showTable ? 'rotate(180deg)' : 'none', transition: 'transform .22s' }}>
                  <path d="M6 9l6 6 6-6" />
                </svg>
              </div>
            </div>

            <div className={`pricing-table-outer${showTable ? ' open' : ''}`} ref={tableWrapRef}>
              <div className="pricing-table-scroll">
                <table className="pricing-table">
                  <thead>
                    <tr className="ptbl-head">
                      <th className="ptbl-th ptbl-th-feature">Feature</th>
                      <th className="ptbl-th">
                        <div className="ptbl-th-label">Free</div>
                        <div className="ptbl-th-price">₹0</div>
                      </th>
                      <th className="ptbl-th ptbl-th-pro">
                        <div className="ptbl-th-label">Pro</div>
                        <div className="ptbl-th-price">₹{(period === 'yearly' ? 200 : 500).toLocaleString('en-IN')}<span>/mo</span></div>
                      </th>
                      <th className="ptbl-th">
                        <div className="ptbl-th-label">Enterprise</div>
                        <div className="ptbl-th-price">Custom</div>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {TABLE.map((row, index) => {
                      const delay = `${index * 0.022}s`;
                      if (row.category) {
                        return (
                          <tr
                            key={row.label}
                            className="ptbl-cat-row"
                            style={{
                              opacity: tableVisible ? 1 : 0,
                              transform: tableVisible ? 'none' : 'translateX(-12px)',
                              transition: `opacity .3s ${delay}, transform .3s ${delay}`,
                            }}
                          >
                            <td colSpan={4}>{row.label}</td>
                          </tr>
                        );
                      }

                      return (
                        <tr
                          key={row.label}
                          className="ptbl-data-row"
                          style={{
                            opacity: tableVisible ? 1 : 0,
                            transform: tableVisible ? 'none' : 'translateY(6px)',
                            transition: `opacity .28s ${delay}, transform .28s ${delay}`,
                          }}
                        >
                          <td className="ptbl-feature-cell">{row.label}</td>
                          <td>{row.free}</td>
                          <td className="ptbl-pro-col">{row.pro}</td>
                          <td>{row.enterprise}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                  <tfoot>
                    <tr className="ptbl-foot" style={{ opacity: tableVisible ? 1 : 0, transition: 'opacity .4s 0.484s' }}>
                      <td />
                      <td>
                        <button className="btn btn-ghost btn-sm" onClick={() => onOpenModal('signup')}>
                          Get Free
                        </button>
                      </td>
                      <td className="ptbl-pro-col">
                        <button className="btn btn-red btn-sm" onClick={() => setShowCheckoutModal(true)}>
                          Get Pro
                        </button>
                      </td>
                      <td>
                        <button className="btn btn-outline-red btn-sm" onClick={() => window.location.assign(getEnterpriseContactUrl())}>
                          Contact Sales
                        </button>
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>

            <div className="pricing-enterprise-cta">
              <div className="pec-corner-tl" />
              <div className="pec-corner-br" />
              <div className="pec-left">
                <div className="pec-eyebrow">// Enterprise</div>
                <h3 className="pec-title">Need custom infrastructure?</h3>
                <p className="pec-sub">
                  Dedicated workers, custom integrations, usage analytics, and a support SLA tailored to your organisation&apos;s scale.
                </p>
              </div>
              <div className="pec-right">
                <div className="pec-features">
                  {[
                    'Custom infrastructure allocation',
                    'Dedicated onboarding assistance',
                    'Usage analytics dashboard',
                    'Priority technical support',
                  ].map((feature) => (
                    <div className="pec-feat" key={feature}>
                      <Check />
                      {feature}
                    </div>
                  ))}
                </div>
                <button className="btn btn-outline-red btn-lg pec-btn" onClick={() => window.location.assign(getEnterpriseContactUrl())}>
                  Contact Sales →
                </button>
              </div>
            </div>

            <div className="pfaq-section">
              <div className="pfaq-header">
                <div className="pricing-hero-eyebrow" style={{ justifyContent: 'center', marginBottom: 12 }}>
                  <div className="pricing-hero-dot" />
                  <span>// FAQ</span>
                </div>
                <h2 className="pfaq-title">Frequently Asked Questions</h2>
                <p className="pfaq-subtitle">Our support team answers these questions every day.</p>
              </div>

              <div className="pfaq-tabs">
                {FAQ_DATA.map((section, index) => (
                  <button
                    key={section.section}
                    className={`pfaq-tab${faqSection === index ? ' active' : ''}`}
                    onClick={() => setFaqSection(index)}
                  >
                    {section.section}
                  </button>
                ))}
              </div>

              <div className="pfaq-items">
                {FAQ_DATA[faqSection].items.map((item, index) => (
                  <FaqItem key={`${faqSection}-${index}`} q={item.q} a={item.a} />
                ))}
              </div>
            </div>

            <div className={`modal-backdrop${showCheckoutModal ? ' open' : ''}`} onClick={() => setShowCheckoutModal(false)}>
              <div className="modal orbit-launch-modal" onClick={(event) => event.stopPropagation()} role="dialog" aria-modal="true" aria-label="Choose Pro subscription">
                <button type="button" className="modal-close" onClick={() => setShowCheckoutModal(false)} aria-label="Close checkout chooser">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
                <div className="modal-logo">
                  <div className="modal-logo-mark">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
                      <circle cx="12" cy="12" r="3" />
                      <circle cx="12" cy="12" r="8" strokeDasharray="4 3" />
                    </svg>
                  </div>
                  <span className="modal-logo-text">Pdf<em>ORBIT</em></span>
                </div>
                <div className="orbit-modal-kicker">// Secure checkout</div>
                <h2>Choose your Pro plan</h2>
                <p className="modal-sub orbit-modal-copy">
                  Both plans unlock 1000 credits per day and verified Pro subscription status. Enterprise still routes through sales.
                </p>
                <PricingPlans onSuccess={() => setShowCheckoutModal(false)} />
                <p className="billing-modal-note">
                  Checkout is powered by Razorpay. Subscription activation only happens after signature and amount verification on the server.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
