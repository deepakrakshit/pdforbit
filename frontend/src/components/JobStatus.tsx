import { API_BASE } from '@/lib/api';
import { fmtBytes } from '@/lib/utils';
import type { JobResponse } from '@/lib/api';
import type { JobStatus as JobStatusType } from '@/lib/jobPoller';

interface JobStatusProps {
  jobId: string;
  status: JobStatusType;
  label: string;
  progress: number;
  result: JobResponse | null;
}

export default function JobStatus({ jobId, status, label, progress, result }: JobStatusProps) {
  const dlUrl = result?.result_url ?? result?.download_url;

  const details: Array<[string, string]> = [];
  if (result) {
    if (result.original_bytes) details.push(['Original size', fmtBytes(result.original_bytes)]);
    if (result.compressed_bytes) details.push(['Result size', fmtBytes(result.compressed_bytes)]);
    if (result.savings_pct) details.push(['Space saved', result.savings_pct + '%']);
    if (result.pages_processed) details.push(['Pages OCR\'d', String(result.pages_processed)]);
    if (result.parts_count) details.push(['Parts created', String(result.parts_count)]);
    if (result.redactions_applied !== undefined) details.push(['Redactions', String(result.redactions_applied)]);
    if (result.different_pages !== undefined) details.push(['Different pages', String(result.different_pages)]);
    if (result.detected_language) details.push(['Detected language', result.detected_language]);
    if (result.word_count) details.push(['Words translated', result.word_count.toLocaleString()]);
  }

  return (
    <div>
      <div className="job-card">
        <div className="job-row">
          <div className={`job-dot${status ? ` ${status}` : ''}`}/>
          <div className="job-status-text">{label}</div>
          <div className="job-id">JOB: {jobId.slice(0, 8)}…</div>
        </div>
        <div className="job-bar">
          <div className="job-bar-fill" style={{ width: `${progress}%` }}/>
        </div>
        {details.length > 0 && (
          <div className="job-details">
            {details.map(([k, v]) => (
              <div key={k} className="job-detail-row">
                <span>{k}</span>
                <span>{v}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      {dlUrl && (
        <a
          className="dl-btn visible"
          href={API_BASE + dlUrl}
          download
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          Download Result
        </a>
      )}
    </div>
  );
}
