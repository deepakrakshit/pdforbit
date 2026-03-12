import { getAccessToken } from '@/lib/auth';

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? '';

export interface UploadResponse {
  file_id: string;
  filename: string;
  size_bytes: number;
  page_count?: number;
  is_encrypted?: boolean;
  expires_at: string;
}

export interface JobResponse {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress?: number;
  error?: string;
  result_url?: string;
  download_url?: string;
  original_bytes?: number;
  compressed_bytes?: number;
  savings_pct?: number;
  pages_processed?: number;
  parts_count?: number;
  redactions_applied?: number;
  different_pages?: number;
  detected_language?: string;
  word_count?: number;
}

function extractApiErrorMessage(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== 'object') {
    return fallback;
  }

  const candidate = payload as {
    detail?: unknown;
    message?: unknown;
    error?: unknown;
  };

  if (typeof candidate.detail === 'string' && candidate.detail.trim()) {
    return candidate.detail;
  }

  if (Array.isArray(candidate.detail) && candidate.detail.length > 0) {
    const messages = candidate.detail
      .map((entry) => {
        if (!entry || typeof entry !== 'object') {
          return null;
        }

        const detailEntry = entry as { msg?: unknown; loc?: unknown };
        const message = typeof detailEntry.msg === 'string' ? detailEntry.msg.trim() : '';
        const location = Array.isArray(detailEntry.loc)
          ? detailEntry.loc.filter((segment): segment is string | number => typeof segment === 'string' || typeof segment === 'number').join(' -> ')
          : '';

        if (!message) {
          return null;
        }

        return location ? `${location}: ${message}` : message;
      })
      .filter((message): message is string => Boolean(message));

    if (messages.length > 0) {
      return messages.join('; ');
    }
  }

  if (typeof candidate.message === 'string' && candidate.message.trim()) {
    return candidate.message;
  }

  if (typeof candidate.error === 'string' && candidate.error.trim()) {
    return candidate.error;
  }

  return fallback;
}

function buildAuthHeaders(extraHeaders?: HeadersInit): HeadersInit {
  const accessToken = getAccessToken();
  return {
    ...(extraHeaders ?? {}),
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
  };
}

export async function uploadFile(file: File): Promise<UploadResponse> {
  const fd = new FormData();
  fd.append('file', file);

  const res = await fetch(`${API_BASE}/api/v1/upload`, {
    method: 'POST',
    headers: buildAuthHeaders(),
    body: fd
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: `HTTP ${res.status}` }));
    throw new Error(extractApiErrorMessage(err, `Upload failed (${res.status})`));
  }

  return res.json() as Promise<UploadResponse>;
}

export async function submitJob(endpoint: string, payload: Record<string, unknown>): Promise<{ job_id: string }> {
  const res = await fetch(`${API_BASE}/api/v1/${endpoint}`, {
    method: 'POST',
    headers: buildAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: `HTTP ${res.status}` }));
    throw new Error(extractApiErrorMessage(err, `Submission failed (${res.status})`));
  }
  return res.json() as Promise<{ job_id: string }>;
}

export async function pollJob(jobId: string): Promise<JobResponse> {
  const res = await fetch(`${API_BASE}/api/v1/jobs/${jobId}`, {
    headers: buildAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: `HTTP ${res.status}` }));
    throw new Error(extractApiErrorMessage(err, `Poll failed (${res.status})`));
  }
  return res.json() as Promise<JobResponse>;
}
