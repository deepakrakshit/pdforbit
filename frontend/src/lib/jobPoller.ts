import { useCallback, useRef } from 'react';
import { pollJob, type JobResponse } from './api';

export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface PollCallbacks {
  onStatus: (status: JobStatus, label: string, progress: number) => void;
  onCompleted: (data: JobResponse) => void;
  onFailed: (error: string) => void;
  onError: (error: string) => void;
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'Queued - waiting for a worker...',
  processing: 'Processing your file...',
  completed: 'Complete!',
  failed: 'Job failed.',
};

export function useJobPoller() {
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const ticksRef = useRef(0);

  const stopPoll = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const startPoll = useCallback((jobId: string, callbacks: PollCallbacks) => {
    stopPoll();
    ticksRef.current = 0;

    intervalRef.current = setInterval(async () => {
      ticksRef.current++;
      try {
        const data = await pollJob(jobId);
        const st = data.status;
        const progress = data.progress ?? 0;
        const label = STATUS_LABELS[st] ?? st;

        callbacks.onStatus(st, label, progress);

        if (st === 'completed') {
          stopPoll();
          callbacks.onCompleted(data);
        } else if (st === 'failed') {
          stopPoll();
          callbacks.onFailed(data.error ?? 'Processing failed.');
        }
      } catch (error) {
        if (ticksRef.current > 60) {
          stopPoll();
          callbacks.onError(error instanceof Error ? error.message : 'Polling error');
        }
      }
    }, 2000);
  }, [stopPoll]);

  return { startPoll, stopPoll };
}
