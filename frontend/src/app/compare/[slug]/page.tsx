import Link from 'next/link';
import { notFound } from 'next/navigation';
import StructuredData from '@/components/seo/StructuredData';
import InternalLinkSections from '@/components/seo/InternalLinkSections';
import { getAllComparisonPages, getComparisonPageBySlug } from '@/lib/seo/comparisons';
import { buildMetadata } from '@/lib/seo/metadata';
import { buildComparisonSchemas } from '@/lib/seo/schema';

export async function generateStaticParams() {
  return getAllComparisonPages().map((page) => ({ slug: page.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const page = getComparisonPageBySlug(slug);

  if (!page) {
    return {};
  }

  return buildMetadata({
    title: `${page.title} | PdfORBIT`,
    description: page.description,
    path: `/compare/${page.slug}`,
    keywords: [page.title.toLowerCase(), `${page.competitor.toLowerCase()} alternative`, 'pdf tools comparison'],
  });
}

export default async function ComparisonPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const page = getComparisonPageBySlug(slug);

  if (!page) {
    notFound();
  }

  return (
    <>
      {buildComparisonSchemas(page).map((schema, index) => (
        <StructuredData key={`${page.slug}-schema-${index}`} data={schema} />
      ))}
      <div className="static-page">
        <div className="static-hero">
          <div className="wrap">
            <div className="static-hero-inner">
              <div className="tag">// Comparison</div>
              <h1>{page.headline}</h1>
              <p>{page.description}</p>
            </div>
          </div>
        </div>
        <div className="static-body">
          <div className="wrap">
            <div className="prose-section">
              <h2>Why searchers compare these tools</h2>
              <p>Comparison pages capture commercial-investigation intent and create natural backlinks when users evaluate alternatives in blog posts, directories, and review threads.</p>
            </div>
            <div className="prose-section">
              <h2>Where PdfORBIT can outperform</h2>
              <ul>
                {page.advantages.map((advantage) => (
                  <li key={advantage}>{advantage}</li>
                ))}
              </ul>
              <p>
                Open the most relevant workflow next, such as <Link href="/tools/merge-pdf">Merge PDF</Link> or <Link href="/tools/compress-pdf">Compress PDF</Link>.
              </p>
            </div>
          </div>
        </div>
      </div>
      <InternalLinkSections toolId={page.relatedToolIds[0]} guideSlugs={['how-to-merge-pdf', 'how-to-compress-pdf']} />
    </>
  );
}