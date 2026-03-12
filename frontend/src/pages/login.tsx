import { useEffect } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import AuthFormCard from '@/components/AuthFormCard';
import { useAuth } from '@/components/AuthProvider';

function resolveRedirectTarget(value: unknown): string {
  if (typeof value !== 'string') {
    return '/';
  }

  if (!value.startsWith('/') || value.startsWith('//')) {
    return '/';
  }

  return value;
}

export default function LoginPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const redirectTarget = resolveRedirectTarget(router.query.redirect);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      void router.replace(redirectTarget);
    }
  }, [isAuthenticated, isLoading, redirectTarget, router]);

  return (
    <>
      <Head>
        <title>Log In | PdfORBIT</title>
        <meta name="description" content="Log in to access your PdfORBIT dashboard, credits, and job history." />
        <meta name="robots" content="noindex,follow" />
      </Head>
      <AuthFormCard mode="login" />
    </>
  );
}