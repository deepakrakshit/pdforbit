import type { AppProps } from 'next/app';
import { useCallback } from 'react';
import { useRouter } from 'next/router';
import { AuthProvider } from '@/components/AuthProvider';
import { ToastProvider } from '@/components/Toast';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import type { ModalType } from '@/components/Modal';
import '@/styles/globals.css';

export default function App({ Component, pageProps }: AppProps) {
  const router = useRouter();

  const openModal = useCallback((type: ModalType) => {
    if (type === 'login') {
      void router.push('/login');
      return;
    }
    if (type === 'signup') {
      void router.push('/signup');
    }
  }, [router]);

  return (
    <AuthProvider>
      <ToastProvider>
        <Navbar onOpenModal={openModal} />
        <Component {...pageProps} onOpenModal={openModal} />
        <Footer />
      </ToastProvider>
    </AuthProvider>
  );
}
