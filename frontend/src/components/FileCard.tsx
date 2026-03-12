import { fmtBytes } from '@/lib/utils';
import type { UploadResponse } from '@/lib/api';

export type FileCardState =
  | { status: 'uploading'; name: string; size: number; progress: number }
  | { status: 'done'; data: UploadResponse }
  | { status: 'error'; name: string; size: number; error: string };

interface FileCardProps {
  id: string;
  state: FileCardState;
  onRemove?: () => void;
}

export default function FileCard({ id, state, onRemove }: FileCardProps) {
  return (
    <div className="file-card" id={id}>
      <div className="file-card-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
      </div>
      <div className="file-card-body">
        {state.status === 'uploading' && (
          <>
            <div className="file-card-name">{state.name}</div>
            <div className="file-card-meta">{fmtBytes(state.size)} · Uploading…</div>
            <div className="fc-progress">
              <div className="fc-progress-fill" style={{ width: `${state.progress}%` }}/>
            </div>
          </>
        )}
        {state.status === 'done' && (
          <>
            <div className="file-card-name">{state.data.filename}</div>
            <div className="file-card-meta">
              {fmtBytes(state.data.size_bytes)}
              {state.data.page_count ? ` · ${state.data.page_count} pages` : ''}
              {state.data.is_encrypted ? ' · 🔒 Encrypted' : ''}
            </div>
            <div className="fc-success">
              ✓ Uploaded — expires {new Date(state.data.expires_at).toLocaleTimeString()}
            </div>
          </>
        )}
        {state.status === 'error' && (
          <>
            <div className="file-card-name">{state.name}</div>
            <div className="file-card-meta">{fmtBytes(state.size)}</div>
            <div className="fc-error">✗ {state.error}</div>
          </>
        )}
      </div>

      {state.status === 'done' && (
        <div className="file-id-tag">
          ID: {state.data.file_id.slice(0, 8)}…
        </div>
      )}

      {onRemove && (
        <button className="file-card-remove" onClick={onRemove} aria-label="Remove file">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      )}
    </div>
  );
}
