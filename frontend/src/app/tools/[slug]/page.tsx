import { notFound } from 'next/navigation';
import StructuredData from '@/components/seo/StructuredData';
import ToolSeoSections from '@/components/seo/ToolSeoSections';
import ToolExperience from '@/components/tools/ToolExperience';
import { buildMetadata } from '@/lib/seo/metadata';
import { buildToolSchemas } from '@/lib/seo/schema';
import { getAllToolSeoEntries, getToolSeoEntryBySlug } from '@/lib/seo/tools';

export async function generateStaticParams() {
  return getAllToolSeoEntries().map((entry) => ({ slug: entry.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const entry = getToolSeoEntryBySlug(slug);

  if (!entry) {
    return {};
  }

  return buildMetadata({
    title: entry.title,
    description: entry.description,
    path: entry.path,
    keywords: entry.keywords,
    image: entry.ogImage,
  });
}

export default async function ToolPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const entry = getToolSeoEntryBySlug(slug);

  if (!entry) {
    notFound();
  }

  return (
    <>
      {buildToolSchemas(entry).map((schema, index) => (
        <StructuredData key={`${entry.slug}-schema-${index}`} data={schema} />
      ))}
      <div className="static-page">
        <div className="static-hero">
          <div className="wrap">
            <div className="static-hero-inner">
              <div className="tag">// {entry.tool.cat}</div>
              <h1>{entry.heroTitle}</h1>
              <p>{entry.intro}</p>
            </div>
          </div>
        </div>
      </div>
      <ToolExperience tool={entry.tool} />
      <ToolSeoSections entry={entry} />
    </>
  );
}