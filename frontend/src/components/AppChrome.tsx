'use client';

import type { ReactNode } from 'react';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import type { ModalType } from '@/components/Modal';

export default function AppChrome({ children }: { children: ReactNode }) {
  const openModal = (type: ModalType) => {
    const destination = type === 'login' ? '/login' : '/signup';
    window.location.assign(destination);
  };

  return (
    <>
      <Navbar onOpenModal={openModal} />
      {children}
      <Footer />
    </>
  );
}