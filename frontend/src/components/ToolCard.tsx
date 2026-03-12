import Link from 'next/link';
import type { Tool } from '@/data/tools';
import { getToolPathById } from '@/lib/seo/routes';

interface ToolCardProps {
  tool: Tool;
}

export default function ToolCard({ tool }: ToolCardProps) {
  return (
    <Link
      className={`tool-card${tool.isNew ? ' has-new' : ''}`}
      role="listitem"
      href={getToolPathById(tool.id)}
    >
      <div className="tool-icon">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.7"
          strokeLinecap="round"
          strokeLinejoin="round"
          dangerouslySetInnerHTML={{ __html: tool.svg }}
        />
      </div>
      <div className="tool-name">{tool.name}</div>
      <div className="tool-desc">{tool.desc}</div>
      <div className="tool-arrow">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M5 12h14m-7-7l7 7-7 7"/>
        </svg>
      </div>
    </Link>
  );
}
