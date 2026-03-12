import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useAuth } from '@/components/AuthProvider';
import { useToast } from '@/components/Toast';

interface AuthFormCardProps {
  mode: 'login' | 'signup';
}

function resolveRedirectTarget(value: unknown): string {
  if (typeof value !== 'string') {
    return '/';
  }

  if (!value.startsWith('/') || value.startsWith('//')) {
    return '/';
  }

  return value;
}

function OrbitLogo() {
  return (
    <div className="auth-brand">
      <div className="auth-brand-mark">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
          <circle cx="12" cy="12" r="3"/>
          <circle cx="12" cy="12" r="8" strokeDasharray="4 3"/>
        </svg>
      </div>
      <span className="auth-brand-text">Pdf<em>ORBIT</em></span>
    </div>
  );
}

export default function AuthFormCard({ mode }: AuthFormCardProps) {
  const router = useRouter();
  const { login, signup } = useAuth();
  const { toast } = useToast();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const redirectTarget = resolveRedirectTarget(router.query.redirect);
  const isSignup = mode === 'signup';

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!email || !password) {
      setError('Email and password are required.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      if (isSignup) {
        await signup(email, password);
        toast('success', 'Account created', 'Your free credit balance is ready to use.');
      } else {
        await login(email, password);
        toast('success', 'Logged in', 'Welcome back to PdfORBIT.');
      }
      await router.push(redirectTarget);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Authentication failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="auth-shell">
      <div className="auth-grid wrap-lg">
        <div className="auth-copy">
          <p className="auth-eyebrow">Secure Document Workspace</p>
          <h1>{isSignup ? 'Create your PdfORBIT account' : 'Access your document dashboard'}</h1>
          <p className="auth-lead">
            {isSignup
              ? 'Start with the free plan, get daily credits, and process documents across the full PdfORBIT toolset.'
              : 'Sign in to manage credits, review processed jobs, and launch document workflows from one dashboard.'}
          </p>
          <div className="auth-feature-list">
            <div className="auth-feature">Daily free credits for core PDF tools</div>
            <div className="auth-feature">Priority plans for OCR, translation, and advanced conversions</div>
            <div className="auth-feature">Persistent job history and download access</div>
          </div>
        </div>

        <div className="auth-card-wrap">
          <div className="auth-card">
            <OrbitLogo />
            <div className="auth-card-head">
              <p className="auth-card-kicker">{isSignup ? 'Free plan' : 'Member access'}</p>
              <h2>{isSignup ? 'Sign up' : 'Log in'}</h2>
              <p>{isSignup ? '30 free credits refresh daily at midnight.' : 'Pick up from the homepage or jump back to your saved workflow.'}</p>
            </div>

            <form className="auth-form" onSubmit={handleSubmit}>
              <label className="auth-field">
                <span>Email</span>
                <input
                  type="email"
                  autoComplete="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </label>

              <label className="auth-field">
                <span>Password</span>
                <input
                  type="password"
                  autoComplete={isSignup ? 'new-password' : 'current-password'}
                  placeholder="At least 8 characters"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </label>

              {error ? <div className="auth-error">{error}</div> : null}

              <button className="btn btn-red btn-lg auth-submit" type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Submitting...' : isSignup ? 'Create account' : 'Log in'}
              </button>
            </form>

            <div className="auth-switcher">
              {isSignup ? 'Already have an account?' : 'Need an account?'}{' '}
              <Link href={isSignup ? '/login' : '/signup'}>{isSignup ? 'Log in' : 'Sign up free'}</Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}