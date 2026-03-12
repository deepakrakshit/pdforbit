import type { ReactNode } from 'react';
import AppChrome from '@/components/AppChrome';
import StructuredData from '@/components/seo/StructuredData';
import { AuthProvider } from '@/components/AuthProvider';
import { ToastProvider } from '@/components/Toast';
import { siteMetadata } from '@/lib/seo/metadata';
import { buildSiteGraph } from '@/lib/seo/schema';
import '@/styles/globals.css';

export const metadata = siteMetadata;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <StructuredData data={buildSiteGraph()} />
        <AuthProvider>
          <ToastProvider>
            <AppChrome>{children}</AppChrome>
          </ToastProvider>
        </AuthProvider>
      </body>
    </html>
  );
}