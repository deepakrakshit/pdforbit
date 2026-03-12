import InternalLinkSections from '@/components/seo/InternalLinkSections';
import type { ToolSeoEntry } from '@/lib/seo/tools';

interface ToolSeoSectionsProps {
  entry: ToolSeoEntry;
}

export default function ToolSeoSections({ entry }: ToolSeoSectionsProps) {
  return (
    <>
      <section className="static-body">
        <div className="wrap">
          <div className="prose-section">
            <div className="tag">// How to use</div>
            <h2>How to use {entry.tool.name}</h2>
            <ol>
              {entry.steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </div>

          <div className="prose-section">
            <div className="tag">// Benefits</div>
            <h2>Why use PdfORBIT for {entry.tool.name}</h2>
            <ul>
              {entry.benefits.map((benefit) => (
                <li key={benefit}>{benefit}</li>
              ))}
            </ul>
          </div>

          <div className="prose-section">
            <div className="tag">// Security</div>
            <h2>Security and file handling</h2>
            <p>{entry.security}</p>
          </div>
        </div>
      </section>

      <InternalLinkSections toolId={entry.tool.id} guideSlugs={entry.guideSlugs} />
    </>
  );
}