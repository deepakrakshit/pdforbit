import Link from 'next/link';
import { notFound } from 'next/navigation';
import InternalLinkSections from '@/components/seo/InternalLinkSections';
import { getAllFeaturePages, getFeaturePageBySlug } from '@/lib/seo/features';
import { buildMetadata } from '@/lib/seo/metadata';

export async function generateStaticParams() {
  return getAllFeaturePages().map((page) => ({ slug: page.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const page = getFeaturePageBySlug(slug);

  if (!page) {
    return {};
  }

  return buildMetadata({
    title: `${page.title} | PdfORBIT`,
    description: page.description,
    path: `/features/${page.slug}`,
    keywords: [page.title.toLowerCase(), 'pdf feature page', 'pdf saas'],
  });
}

export default async function FeaturePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const page = getFeaturePageBySlug(slug);

  if (!page) {
    notFound();
  }

  return (
    <>
      <div className="static-page">
        <div className="static-hero">
          <div className="wrap">
            <div className="static-hero-inner">
              <div className="tag">// Feature</div>
              <h1>{page.headline}</h1>
              <p>{page.description}</p>
            </div>
          </div>
        </div>
        <div className="static-body">
          <div className="wrap">
            <div className="prose-section">
              <h2>Feature context</h2>
              <p>{page.intro}</p>
              <p>
                Move from feature research into execution through the canonical tool directory, starting with{' '}
                <Link href="/tools">all tools</Link>.
              </p>
            </div>
          </div>
        </div>
      </div>
      <InternalLinkSections toolId={page.relatedToolIds[0]} guideSlugs={['how-to-edit-pdf-online', 'how-to-compress-pdf']} />
    </>
  );
}