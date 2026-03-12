import Link from 'next/link';
import { notFound } from 'next/navigation';
import StructuredData from '@/components/seo/StructuredData';
import InternalLinkSections from '@/components/seo/InternalLinkSections';
import { getBlogPostBySlug, getAllBlogPosts } from '@/lib/seo/blog';
import { buildMetadata } from '@/lib/seo/metadata';
import { buildBlogSchemas } from '@/lib/seo/schema';
import { getToolPathById } from '@/lib/seo/routes';

export async function generateStaticParams() {
  return getAllBlogPosts().map((post) => ({ slug: post.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const post = getBlogPostBySlug(slug);

  if (!post) {
    return {};
  }

  return buildMetadata({
    title: `${post.title} | PdfORBIT`,
    description: post.description,
    path: `/blog/${post.slug}`,
    keywords: post.keywords,
  });
}

export default async function BlogPostPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const post = getBlogPostBySlug(slug);

  if (!post) {
    notFound();
  }

  return (
    <>
      {buildBlogSchemas(post).map((schema, index) => (
        <StructuredData key={`${post.slug}-schema-${index}`} data={schema} />
      ))}
      <div className="static-page">
        <div className="static-hero">
          <div className="wrap">
            <div className="static-hero-inner">
              <div className="tag">// Blog</div>
              <h1>{post.title}</h1>
              <p>{post.answerSnippet}</p>
            </div>
          </div>
        </div>
        <div className="static-body">
          <div className="wrap">
            <div className="prose-section">
              <h2>Quick answer</h2>
              <p>{post.answerSnippet}</p>
              <p>
                Ready to act on it? Open the first matching tool:{' '}
                <Link href={getToolPathById(post.relatedToolIds[0])}>launch the workflow</Link>.
              </p>
            </div>

            <div className="prose-section">
              <h2>Step-by-step instructions</h2>
              <ol>
                {post.steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            </div>

            {post.sections.map((section) => (
              <div key={section.heading} className="prose-section">
                <h2>{section.heading}</h2>
                <p>{section.body}</p>
              </div>
            ))}

            <div className="prose-section">
              <h2>FAQ</h2>
              {post.faq.map((item) => (
                <div key={item.question}>
                  <h3>{item.question}</h3>
                  <p>{item.answer}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      <InternalLinkSections toolId={post.relatedToolIds[0]} guideSlugs={post.relatedGuideSlugs} />
    </>
  );
}