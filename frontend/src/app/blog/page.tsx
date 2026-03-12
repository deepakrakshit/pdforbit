import Link from 'next/link';
import { buildMetadata } from '@/lib/seo/metadata';
import { getAllBlogPosts } from '@/lib/seo/blog';

export const metadata = buildMetadata({
  title: 'PDF Guides and Tutorials | PdfORBIT Blog',
  description: 'Search-focused guides for merging, compressing, editing, converting, and optimizing PDF workflows.',
  path: '/blog',
  keywords: ['pdf blog', 'pdf guides', 'how to merge pdf', 'how to compress pdf'],
});

export default function BlogIndexPage() {
  const posts = getAllBlogPosts();

  return (
    <div className="static-page">
      <div className="static-hero">
        <div className="wrap">
          <div className="static-hero-inner">
            <div className="tag">// Organic growth engine</div>
            <h1>PDF guides built for real search intent</h1>
            <p>Every article is designed to answer a specific problem, route users into the right tool, and deepen the internal linking graph.</p>
          </div>
        </div>
      </div>
      <div className="static-body">
        <div className="wrap">
          <div className="status-grid">
            {posts.map((post) => (
              <article key={post.slug} className="status-card">
                <h2>
                  <Link href={`/blog/${post.slug}`}>{post.title}</Link>
                </h2>
                <p>{post.excerpt}</p>
              </article>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}