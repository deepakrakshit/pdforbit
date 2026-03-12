import { useState } from 'react';
import type { Tool } from '@/data/tools';
import { getToolFaqs } from '@/data/toolFaqs';

interface ToolFaqSectionProps {
  tool: Tool;
}

export default function ToolFaqSection({ tool }: ToolFaqSectionProps) {
  const faqs = getToolFaqs(tool);
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <section className="tool-faq-section">
      <div className="tool-faq-head">
        <div className="tool-faq-kicker">// Tool FAQ</div>
        <h2>{tool.name} questions answered</h2>
        <p>Quick answers for this workflow so users know what to expect before they upload, process, and download.</p>
      </div>

      <div className="faq-list">
        {faqs.map((faq, index) => {
          const isOpen = openIndex === index;
          return (
            <div key={faq.q} className={`faq-item${isOpen ? ' open' : ''}`} onClick={() => setOpenIndex(isOpen ? null : index)}>
              <div className="faq-q">
                <span className="faq-q-text">{faq.q}</span>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16" style={{ transform: isOpen ? 'rotate(180deg)' : 'none', transition: 'transform .2s' }}>
                  <path d="M6 9l6 6 6-6"/>
                </svg>
              </div>
              {isOpen ? <div className="faq-a">{faq.a}</div> : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}