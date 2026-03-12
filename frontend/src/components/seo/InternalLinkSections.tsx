import Link from 'next/link';
import type { BlogPost } from '@/lib/seo/blog';
import { getBlogPostBySlug } from '@/lib/seo/blog';
import { getToolPathById } from '@/lib/seo/routes';
import { getRelatedToolSeoEntries } from '@/lib/seo/tools';

interface InternalLinkSectionsProps {
  toolId: string;
  guideSlugs: string[];
}

export default function InternalLinkSections({ toolId, guideSlugs }: InternalLinkSectionsProps) {
  const relatedTools = getRelatedToolSeoEntries(toolId);
  const relatedGuides = guideSlugs
    .map((slug) => getBlogPostBySlug(slug))
    .filter((guide): guide is BlogPost => Boolean(guide));

  return (
    <div className="static-body">
      <div className="wrap">
        <div className="status-grid">
          <section className="status-card">
            <h3>Related tools</h3>
            <ul>
              {relatedTools.map((tool) => (
                <li key={tool.tool.id}>
                  <Link href={getToolPathById(tool.tool.id)}>{tool.tool.name}</Link>
                </li>
              ))}
            </ul>
          </section>

          <section className="status-card">
            <h3>Popular tasks</h3>
            <ul>
              {relatedTools.slice(0, 3).map((tool) => (
                <li key={`${tool.tool.id}-task`}>
                  <Link href={getToolPathById(tool.tool.id)}>{tool.heroTitle}</Link>
                </li>
              ))}
            </ul>
          </section>

          <section className="status-card">
            <h3>Related guides</h3>
            <ul>
              {relatedGuides.map((guide) => (
                <li key={guide.slug}>
                  <Link href={`/blog/${guide.slug}`}>{guide.title}</Link>
                </li>
              ))}
            </ul>
          </section>
        </div>
      </div>
    </div>
  );
}