import { Html, Head, Main, NextScript } from 'next/document';
import { SITE_DEFAULT_DESCRIPTION, SITE_DEFAULT_OG_IMAGE, SITE_DEFAULT_TITLE, SITE_LOGO_MARK_PATH, SITE_NAME, SITE_URL, absoluteUrl } from '@/lib/seo/site';

export default function Document() {
  const defaultOgImage = absoluteUrl(SITE_DEFAULT_OG_IMAGE);

  return (
    <Html lang="en">
      <Head>
        <meta name="google-site-verification" content="EM5NjBSaslL4nTdW_6h6LRVRuBuR6mgTunAkCpB67eE" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=Barlow+Condensed:ital,wght@0,300;0,400;0,500;0,600;0,700;1,300&family=DM+Mono:ital,wght@0,300;0,400;0,500;1,300&display=swap" rel="stylesheet" />
        <meta name="application-name" content={SITE_NAME} />
        <meta name="theme-color" content="#0b1220" />
        <meta property="og:site_name" content={SITE_NAME} />
        <meta property="og:type" content="website" />
        <meta property="og:title" content={SITE_DEFAULT_TITLE} />
        <meta property="og:description" content={SITE_DEFAULT_DESCRIPTION} />
        <meta property="og:url" content={SITE_URL} />
        <meta property="og:image" content={defaultOgImage} />
        <meta property="og:image:alt" content="PdfORBIT logo and brand artwork" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={SITE_DEFAULT_TITLE} />
        <meta name="twitter:description" content={SITE_DEFAULT_DESCRIPTION} />
        <meta name="twitter:image" content={defaultOgImage} />
        <link rel="manifest" href="/site.webmanifest" />
        <link rel="icon" href={SITE_LOGO_MARK_PATH} type="image/svg+xml" />
        <link rel="apple-touch-icon" href={SITE_LOGO_MARK_PATH} />
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
