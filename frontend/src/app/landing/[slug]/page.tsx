import Link from 'next/link';
import { notFound } from 'next/navigation';
import StructuredData from '@/components/seo/StructuredData';
import InternalLinkSections from '@/components/seo/InternalLinkSections';
import { getLandingPageBySlug, getAllLandingPages } from '@/lib/seo/landings';
import { buildMetadata } from '@/lib/seo/metadata';
import { buildLandingSchemas } from '@/lib/seo/schema';
import { getToolPathById } from '@/lib/seo/routes';

export async function generateStaticParams() {
  return getAllLandingPages().map((page) => ({ slug: page.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const page = getLandingPageBySlug(slug);

  if (!page) {
    return {};
  }

  return buildMetadata({
    title: `${page.title} | PdfORBIT`,
    description: page.description,
    path: `/${page.slug}`,
    keywords: page.keywords,
  });
}

export default async function LandingPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const page = getLandingPageBySlug(slug);

  if (!page) {
    notFound();
  }

  return (
    <>
      {buildLandingSchemas(page).map((schema, index) => (
        <StructuredData key={`${page.slug}-schema-${index}`} data={schema} />
      ))}
      <div className="static-page">
        <div className="static-hero">
          <div className="wrap">
            <div className="static-hero-inner">
              <div className="tag">// Landing page</div>
              <h1>{page.title}</h1>
              <p>{page.hero}</p>
            </div>
          </div>
        </div>
        <div className="static-body">
          <div className="wrap">
            <div className="prose-section">
              <h2>Why this page exists</h2>
              <p>{page.intro}</p>
            </div>
            <div className="prose-section">
              <h2>Suggested workflow preset</h2>
              <p>{page.useCase}</p>
              <pre>{JSON.stringify(page.preset, null, 2)}</pre>
              <p>
                Start the workflow in the main tool at <Link href={getToolPathById(page.toolId)}>{getToolPathById(page.toolId)}</Link>.
              </p>
            </div>
            <div className="prose-section">
              <h2>FAQ</h2>
              {page.faq.map((item) => (
                <div key={item.question}>
                  <h3>{item.question}</h3>
                  <p>{item.answer}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      <InternalLinkSections toolId={page.toolId} guideSlugs={page.relatedGuideSlugs} />
    </>
  );
}