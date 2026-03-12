import { useCallback, useEffect, useMemo, useState } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import UploadZone from '@/components/UploadZone';
import { useAuth } from '@/components/AuthProvider';
import { useToast } from '@/components/Toast';
import { uploadFile, type UploadResponse } from '@/lib/api';
import { getToolPathById } from '@/lib/seo/routes';
import type { Tool } from '@/data/tools';

const DASHBOARD_UPLOAD_TOOL: Tool = {
  id: 'dashboard-upload',
  cat: 'dashboard',
  name: 'Dashboard Upload',
  desc: 'Upload files to your workspace.',
  accept: '.pdf,.jpg,.jpeg,.png,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.html,.htm,.bmp,.tiff,.webp',
  svg: '<path d="M12 16V4m0 0L8 8m4-4 4 4"/><path d="M20 16.58A5 5 0 0018 7h-1.26A8 8 0 103 15.25"/>',
};

export default function DashboardPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading, refreshUser } = useAuth();
  const { toast } = useToast();
  const [uploads, setUploads] = useState<UploadResponse[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      void router.replace(`/login?redirect=${encodeURIComponent('/dashboard')}`);
    }
  }, [isAuthenticated, isLoading, router]);

  useEffect(() => {
    if (isAuthenticated) {
      void refreshUser();
    }
  }, [isAuthenticated, refreshUser]);

  const creditLabel = useMemo(() => {
    if (!user) {
      return '--';
    }
    if (user.is_admin) {
      return 'Unlimited';
    }
    return `${user.credits_remaining} / ${user.credit_limit}`;
  }, [user]);

  const handleFiles = useCallback(async (files: File[]) => {
    setIsUploading(true);
    try {
      const completedUploads: UploadResponse[] = [];
      for (const file of files) {
        completedUploads.push(await uploadFile(file));
      }
      setUploads((previous) => [...completedUploads.reverse(), ...previous].slice(0, 6));
      toast('success', 'Upload complete', `${completedUploads.length} file${completedUploads.length > 1 ? 's' : ''} added to your workspace.`);
      await refreshUser();
    } catch (error) {
      toast('error', 'Upload failed', error instanceof Error ? error.message : 'Unable to upload the selected file.');
    } finally {
      setIsUploading(false);
    }
  }, [refreshUser, toast]);

  if (!user && isLoading) {
    return <div className="dashboard-loading">Loading your workspace…</div>;
  }

  if (!user) {
    return null;
  }

  const planLabel = user.is_admin ? 'INTERNAL ADMIN' : user.plan_type.toUpperCase();
  const planCopy = user.is_admin
    ? 'Unlimited internal account for development and QA workflows.'
    : user.plan_type === 'free'
      ? 'Daily credits reset automatically at midnight.'
      : 'Daily credit allowance for heavier workflows.';
  const creditCopy = user.is_admin
    ? 'Credit deduction is bypassed for internal testing.'
    : user.plan_type === 'free'
      ? 'Free plan: 30 credits per day. Most tools cost 1 credit.'
      : 'Pro plan: 1000 credits per day. Translate and Summarize cost 5 credits.';

  return (
    <>
      <Head>
        <title>Dashboard | PdfORBIT</title>
        <meta name="description" content="Manage your PdfORBIT plan, credits, uploads, and document workflows." />
        <meta name="robots" content="noindex,follow" />
      </Head>

      <div className="dashboard-page">
        <section className="dashboard-hero wrap-lg">
          <div>
            <p className="dashboard-eyebrow">Member workspace</p>
            <h1>Document control, credits, and processing in one place.</h1>
            <p className="dashboard-copy">Review your plan, upload new files, and jump straight into PdfORBIT processing tools without leaving your workspace.</p>
          </div>
          <div className="dashboard-hero-actions">
            <Link href="/pricing" className="btn btn-red btn-lg">Upgrade to Pro</Link>
            <Link href={getToolPathById('merge')} className="btn btn-ghost btn-lg">Open Tool Suite</Link>
          </div>
        </section>

        <section className="dashboard-metrics wrap-lg">
          <div className="dashboard-stat-card">
            <span className="dashboard-stat-label">Plan</span>
            <strong>{planLabel}</strong>
            <p>{planCopy}</p>
          </div>
          <div className="dashboard-stat-card emphasis">
            <span className="dashboard-stat-label">Credits Remaining</span>
            <strong>{creditLabel}</strong>
            <p>{creditCopy}</p>
          </div>
          <div className="dashboard-stat-card">
            <span className="dashboard-stat-label">Jobs Processed</span>
            <strong>{user.jobs_processed}</strong>
            <p>Completed document workflows tied to your account.</p>
          </div>
        </section>

        <section className="dashboard-workspace wrap-lg">
          <div className="dashboard-upload-panel">
            <div className="dashboard-panel-head">
              <div>
                <p className="dashboard-panel-kicker">Upload area</p>
                <h2>Add files to your workspace</h2>
              </div>
              {isUploading ? <span className="dashboard-status-pill">Uploading…</span> : null}
            </div>

            <UploadZone
              tool={DASHBOARD_UPLOAD_TOOL}
              onFiles={handleFiles}
              isDragOver={isDragOver}
              onDragOver={() => setIsDragOver(true)}
              onDragLeave={() => setIsDragOver(false)}
            />
          </div>

          <aside className="dashboard-side-panel">
            <div className="dashboard-panel-head compact">
              <div>
                <p className="dashboard-panel-kicker">Quick actions</p>
                <h2>Launch a tool</h2>
              </div>
            </div>
            <div className="dashboard-quick-grid">
              <Link href={getToolPathById('compress')} className="dashboard-quick-link">Compress PDF</Link>
              <Link href={getToolPathById('merge')} className="dashboard-quick-link">Merge PDF</Link>
              <Link href={getToolPathById('split')} className="dashboard-quick-link">Split PDF</Link>
              <Link href={getToolPathById('ocr')} className="dashboard-quick-link">OCR PDF</Link>
            </div>
          </aside>
        </section>

        <section className="dashboard-uploads wrap-lg">
          <div className="dashboard-panel-head compact">
            <div>
              <p className="dashboard-panel-kicker">Recent uploads</p>
              <h2>Files you added this session</h2>
            </div>
          </div>

          {uploads.length === 0 ? (
            <div className="dashboard-empty">Upload a file to start building your workspace queue.</div>
          ) : (
            <div className="dashboard-upload-list">
              {uploads.map((upload) => (
                <article key={upload.file_id} className="dashboard-upload-item">
                  <div>
                    <strong>{upload.filename}</strong>
                    <p>File ID: {upload.file_id}</p>
                  </div>
                  <span>{Math.round(upload.size_bytes / 1024)} KB</span>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </>
  );
}