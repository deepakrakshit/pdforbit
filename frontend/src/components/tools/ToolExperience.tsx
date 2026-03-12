'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import Link from 'next/link';

import UploadZone from '@/components/UploadZone';
import FileCard from '@/components/FileCard';
import type { FileCardState } from '@/components/FileCard';
import JobStatusComponent from '@/components/JobStatus';
import PdfEditor from '@/components/pdf-editor/PdfEditor';
import ToolFaqSection from '@/components/ToolFaqSection';
import ToolOptions from '@/components/ToolOptions';
import { useAuth } from '@/components/AuthProvider';
import { useToast } from '@/components/Toast';
import { EP } from '@/data/tools';
import type { Tool } from '@/data/tools';
import { API_BASE, submitJob as apiSubmitJob, uploadFile } from '@/lib/api';
import type { JobResponse, UploadResponse } from '@/lib/api';
import { useJobPoller } from '@/lib/jobPoller';
import type { JobStatus } from '@/lib/jobPoller';
import { getToolPathById } from '@/lib/seo/routes';
import { generateId, parsePages } from '@/lib/utils';

interface ToolExperienceProps {
  tool: Tool;
}

interface FileEntry {
  id: string;
  state: FileCardState;
}

type AttachmentKey = 'watermarkImage' | 'signImage' | 'signCert';

function getFieldValue(id: string): string {
  if (typeof document === 'undefined') return '';
  const el = document.getElementById(id) as HTMLInputElement | HTMLSelectElement | null;
  return el ? el.value.trim() : '';
}

function getCheckboxValue(id: string): boolean {
  if (typeof document === 'undefined') return false;
  const el = document.getElementById(id) as HTMLInputElement | null;
  return Boolean(el?.checked);
}

function parseStringList(value: string): string[] {
  return value.split(',').map((item) => item.trim()).filter(Boolean);
}

function parseOptionalInteger(value: string): number | undefined {
  if (!value.trim()) return undefined;
  const parsed = parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function parseOptionalFloat(value: string): number | undefined {
  if (!value.trim()) return undefined;
  const parsed = parseFloat(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function hasUploadedFiles(entries: FileEntry[]): boolean {
  return entries.some((entry) => entry.state.status === 'done' || entry.state.status === 'uploading');
}

function currentPath(): string {
  if (typeof window === 'undefined') {
    return '/';
  }

  return `${window.location.pathname}${window.location.search}`;
}

function navigate(path: string) {
  if (typeof window !== 'undefined') {
    window.location.assign(path);
  }
}

function buildPayload(
  toolId: string,
  primaryFileId: string | null,
  extraFileIds: string[],
  attachments: Record<AttachmentKey, UploadResponse | null>,
): Record<string, unknown> {
  const v = getFieldValue;
  const c = getCheckboxValue;
  const base = primaryFileId ? { file_id: primaryFileId } : {};

  if (toolId === 'merge') {
    return { file_ids: [primaryFileId, ...extraFileIds].filter(Boolean), output_filename: v('f-output') || 'merged.pdf' };
  }

  if (toolId === 'split') {
    const mode = v('f-mode') || 'by_range';
    return {
      ...base,
      mode,
      ranges: mode === 'by_range' ? v('f-ranges') : undefined,
      every_n_pages: mode === 'every_n_pages' ? parseOptionalInteger(v('f-every-n')) ?? 5 : undefined,
      output_prefix: v('f-output-prefix') || 'part',
    };
  }

  if (toolId === 'extract') return { ...base, pages: parsePages(v('f-pages')), output_filename: v('f-output') || 'extracted.pdf' };
  if (toolId === 'remove') return { ...base, pages_to_remove: parsePages(v('f-pages')), output_filename: v('f-output') || 'modified.pdf' };
  if (toolId === 'reorder') return { ...base, page_order: parsePages(v('f-order')), output_filename: v('f-output') || 'reordered.pdf' };
  if (toolId === 'compress') return { ...base, level: v('f-level') || 'medium', output_filename: v('f-output') || 'compressed.pdf' };
  if (toolId === 'repair') return { ...base, output_filename: v('f-output') || 'repaired.pdf' };
  if (toolId === 'ocr') return { ...base, language: v('f-lang') || 'eng', dpi: parseOptionalInteger(v('f-dpi')) ?? 300, output_filename: v('f-output') || 'searchable.pdf' };

  if (toolId === 'img2pdf') {
    const allFileIds = [primaryFileId, ...extraFileIds].filter((fileId): fileId is string => Boolean(fileId));
    return {
      ...(allFileIds.length > 1 ? { file_ids: allFileIds } : { file_id: allFileIds[0] }),
      dpi: parseOptionalInteger(v('f-dpi')) ?? 300,
      page_size: v('f-convert-pagesize') || 'original',
      output_filename: v('f-output') || 'images.pdf',
    };
  }

  if (toolId === 'word2pdf') return { ...base, output_filename: v('f-output') || 'document.pdf' };
  if (toolId === 'excel2pdf') return { ...base, output_filename: v('f-output') || 'spreadsheet.pdf' };
  if (toolId === 'ppt2pdf') return { ...base, include_speaker_notes: c('f-include-speaker-notes'), output_filename: v('f-output') || 'presentation.pdf' };

  if (toolId === 'html2pdf') {
    const sourceMode = v('f-html-source') || 'file';
    if (sourceMode === 'url') {
      return {
        url: v('f-html-url'),
        page_size: v('f-pagesize') || 'A4',
        output_filename: v('f-output') || 'webpage.pdf',
      };
    }
    return { ...base, page_size: v('f-pagesize') || 'A4', output_filename: v('f-output') || 'webpage.pdf' };
  }

  if (toolId === 'pdf2img') {
    return {
      ...base,
      format: v('f-fmt') || 'jpg',
      dpi: parseOptionalInteger(v('f-dpi')) ?? 150,
      quality: parseOptionalInteger(v('f-quality')) ?? 85,
      single_page: parseOptionalInteger(v('f-single-page')),
      thumbnail: c('f-thumbnail'),
      thumbnail_max_px: parseOptionalInteger(v('f-thumbnail-max')) ?? 512,
    };
  }

  if (toolId === 'pdf2word') return { ...base, format: 'word', output_filename: v('f-output') || 'converted.docx' };
  if (toolId === 'pdf2excel') return { ...base, format: 'excel', output_filename: v('f-output') || 'converted.xlsx' };
  if (toolId === 'pdf2ppt') return { ...base, format: 'ppt', output_filename: v('f-output') || 'converted.pptx' };
  if (toolId === 'pdf2pdfa') return { ...base, pdfa_level: v('f-pdfa') || '1b', output_filename: v('f-output') || 'archived.pdf' };

  if (toolId === 'rotate') {
    return {
      ...base,
      angle: parseOptionalInteger(v('f-angle')) ?? 90,
      pages: parsePages(v('f-pages')),
      relative: c('f-rotate-relative'),
      output_filename: v('f-output') || 'rotated.pdf',
    };
  }

  if (toolId === 'watermark') {
    return {
      ...base,
      text: v('f-text') || 'CONFIDENTIAL',
      position: v('f-position') || 'diagonal',
      opacity: parseOptionalFloat(v('f-opacity')) ?? 0.3,
      font_size: parseOptionalInteger(v('f-fontsize')) ?? 72,
      rotation: parseOptionalInteger(v('f-rotation')) ?? 45,
      color: v('f-watermark-color') || '#000000',
      font_family: v('f-watermark-font') || undefined,
      skip_pages: parsePages(v('f-watermark-skip-pages')),
      first_page_only: c('f-watermark-first-page-only'),
      image_upload_id: attachments.watermarkImage?.file_id,
      output_filename: v('f-output') || 'watermarked.pdf',
    };
  }

  if (toolId === 'pagenums') {
    return {
      ...base,
      position: v('f-position') || 'bottom_center',
      start_number: parseOptionalInteger(v('f-start')) ?? 1,
      font_size: parseOptionalInteger(v('f-fontsize')) ?? 12,
      color: v('f-color') || '#000000',
      prefix: v('f-prefix'),
      suffix: v('f-suffix'),
      font_family: v('f-pagenums-font') || undefined,
      numbering_style: v('f-numbering-style') || 'arabic',
      skip_first_n_pages: parseOptionalInteger(v('f-skip-first')) ?? 0,
      skip_last_n_pages: parseOptionalInteger(v('f-skip-last')) ?? 0,
      background_box: c('f-background-box'),
      output_filename: v('f-output') || 'numbered.pdf',
    };
  }

  if (toolId === 'crop') {
    return {
      ...base,
      left: parseOptionalFloat(v('f-left')),
      bottom: parseOptionalFloat(v('f-bottom')),
      right: parseOptionalFloat(v('f-right')),
      top: parseOptionalFloat(v('f-top')),
      pages: parsePages(v('f-pages')),
      auto_crop_whitespace: c('f-auto-crop'),
      permanent_crop: c('f-permanent-crop'),
      output_filename: v('f-output') || 'cropped.pdf',
    };
  }

  if (toolId === 'unlock') return { ...base, password: v('f-password'), output_filename: v('f-output') || 'unlocked.pdf' };

  if (toolId === 'protect') {
    return {
      ...base,
      user_password: v('f-upwd') || undefined,
      owner_password: v('f-opwd') || undefined,
      encryption: parseOptionalInteger(v('f-enc')) ?? 256,
      allow_printing: c('f-allow-printing'),
      allow_copying: c('f-allow-copying'),
      allow_annotations: c('f-allow-annotations'),
      allow_form_filling: c('f-allow-form-filling'),
      output_filename: v('f-output') || 'protected.pdf',
    };
  }

  if (toolId === 'sign') {
    return {
      ...base,
      signature_text: v('f-sigtext') || undefined,
      page: parseOptionalInteger(v('f-page')) ?? 1,
      x: parseOptionalFloat(v('f-x')) ?? 60,
      y: parseOptionalFloat(v('f-y')) ?? 700,
      width: parseOptionalFloat(v('f-width')) ?? 200,
      height: parseOptionalFloat(v('f-height')) ?? 80,
      use_digital_signature: getCheckboxValue('f-sign-digital'),
      cert_password: v('f-sign-cert-password') || undefined,
      cert_file_id: attachments.signCert?.file_id,
      border_style: v('f-sign-border') || 'box',
      include_timestamp: c('f-sign-timestamp'),
      signature_image_upload_id: attachments.signImage?.file_id,
      output_filename: v('f-output') || 'signed.pdf',
    };
  }

  if (toolId === 'redact') {
    return {
      ...base,
      keywords: parseStringList(v('f-keywords')),
      patterns: parseStringList(v('f-regex')),
      fill_color: v('f-rcolor') || '#000000',
      preview_mode: c('f-redact-preview'),
      whole_word: c('f-redact-whole-word'),
      output_filename: v('f-output') || 'redacted.pdf',
    };
  }

  if (toolId === 'compare') {
    return {
      file_id_a: primaryFileId,
      file_id_b: extraFileIds[0] || v('f-file-b'),
      diff_mode: v('f-compare-mode') || 'combined',
      output_filename: v('f-output') || 'comparison.zip',
    };
  }

  if (toolId === 'translate') return { ...base, target_language: v('f-target') || 'en', source_language: v('f-source') || null, output_filename: v('f-output') || 'translated.pdf' };

  if (toolId === 'summarize') {
    return {
      ...base,
      output_language: v('f-summary-lang') || 'en',
      length: v('f-summary-length') || 'medium',
      focus: v('f-summary-focus') || null,
      output_filename: v('f-output') || 'orbit-brief.pdf',
    };
  }

  return base;
}

export default function ToolExperience({ tool }: ToolExperienceProps) {
  const { toast } = useToast();
  const { isAuthenticated, isLoading, refreshUser } = useAuth();
  const { startPoll, stopPoll } = useJobPoller();
  const formRef = useRef<HTMLDivElement>(null);
  const isEditorTool = tool.id === 'editor';

  const [files, setFiles] = useState<FileEntry[]>([]);
  const [primaryFile, setPrimaryFile] = useState<UploadResponse | null>(null);
  const [extraFiles, setExtraFiles] = useState<UploadResponse[]>([]);
  const [editorPreviewUrl, setEditorPreviewUrl] = useState<string | null>(null);
  const [attachments, setAttachments] = useState<Record<AttachmentKey, UploadResponse | null>>({
    watermarkImage: null,
    signImage: null,
    signCert: null,
  });
  const [isDragOver, setIsDragOver] = useState(false);
  const [showOptions, setShowOptions] = useState(tool.id === 'html2pdf');
  const [processing, setProcessing] = useState(false);

  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus>('pending');
  const [jobLabel, setJobLabel] = useState('');
  const [jobProgress, setJobProgress] = useState(0);
  const [jobResult, setJobResult] = useState<JobResponse | null>(null);
  const [showJob, setShowJob] = useState(false);
  const showEditor = isEditorTool && Boolean(primaryFile) && Boolean(editorPreviewUrl);

  const replaceEditorPreviewUrl = useCallback((nextUrl: string | null) => {
    setEditorPreviewUrl((prev) => {
      if (prev && prev !== nextUrl && prev.startsWith('blob:')) {
        URL.revokeObjectURL(prev);
      }
      return nextUrl;
    });
  }, []);

  useEffect(() => {
    return () => {
      if (editorPreviewUrl && editorPreviewUrl.startsWith('blob:')) {
        URL.revokeObjectURL(editorPreviewUrl);
      }
    };
  }, [editorPreviewUrl]);

  useEffect(() => {
    if (!showEditor) {
      return undefined;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [showEditor]);

  const resetTool = useCallback(() => {
    stopPoll();
    setFiles([]);
    setPrimaryFile(null);
    setExtraFiles([]);
    replaceEditorPreviewUrl(null);
    setAttachments({ watermarkImage: null, signImage: null, signCert: null });
    setShowOptions(tool.id === 'html2pdf');
    setProcessing(false);
    setJobId(null);
    setJobStatus('pending');
    setJobLabel('');
    setJobProgress(0);
    setJobResult(null);
    setShowJob(false);
  }, [replaceEditorPreviewUrl, stopPoll, tool.id]);

  const ensureAuthenticated = useCallback(() => {
    if (isAuthenticated) {
      return true;
    }

    if (isLoading) {
      toast('info', 'Checking session', 'Please wait a moment and try again.');
      return false;
    }

    toast('info', 'Login required', 'Create an account or log in to process files.');
    navigate(`/login?redirect=${encodeURIComponent(currentPath())}`);
    return false;
  }, [isAuthenticated, isLoading, toast]);

  const doUpload = useCallback(async (file: File, isExtra: boolean) => {
    if (!ensureAuthenticated()) {
      return;
    }

    const cardId = `fc-${generateId()}`;
    const initEntry: FileEntry = {
      id: cardId,
      state: { status: 'uploading', name: file.name, size: file.size, progress: 0 },
    };

    setFiles((prev) => (isExtra ? [...prev, initEntry] : [initEntry]));

    let progress = 0;
    const ticker = setInterval(() => {
      progress = Math.min(progress + 10, 88);
      setFiles((prev) =>
        prev.map((entry) =>
          entry.id === cardId && entry.state.status === 'uploading'
            ? { ...entry, state: { ...entry.state, progress } as FileCardState }
            : entry,
        ),
      );
    }, 150);

    try {
      const data = await uploadFile(file);
      clearInterval(ticker);

      setFiles((prev) => prev.map((entry) => (entry.id === cardId ? { ...entry, state: { status: 'done', data } } : entry)));
      if (isExtra) {
        setExtraFiles((prev) => [...prev, data]);
      } else {
        setPrimaryFile(data);
        setShowOptions(true);
        if (isEditorTool) {
          replaceEditorPreviewUrl(URL.createObjectURL(file));
        }
      }
      toast('success', 'File uploaded', `${data.filename} ready for processing.`);
    } catch (error) {
      clearInterval(ticker);
      const message = error instanceof Error ? error.message : 'Upload failed';
      setFiles((prev) =>
        prev.map((entry) =>
          entry.id === cardId
            ? { ...entry, state: { status: 'error', name: file.name, size: file.size, error: message } }
            : entry,
        ),
      );
      toast('error', 'Upload failed', message);
    }
  }, [ensureAuthenticated, isEditorTool, replaceEditorPreviewUrl, toast]);

  const handleFiles = useCallback(async (newFiles: File[]) => {
    if (tool.multi) {
      const appendToExistingSelection = Boolean(primaryFile) || hasUploadedFiles(files);

      if (!appendToExistingSelection) {
        await doUpload(newFiles[0], false);
        for (const file of newFiles.slice(1)) {
          await doUpload(file, true);
        }
      } else {
        for (const file of newFiles) {
          await doUpload(file, true);
        }
      }
      return;
    }

    resetTool();
    await doUpload(newFiles[0], false);
  }, [tool.multi, primaryFile, files, doUpload, resetTool]);

  const selectAttachment = useCallback((key: AttachmentKey, accept: string) => {
    if (!ensureAuthenticated()) {
      return;
    }

    const input = document.createElement('input');
    input.type = 'file';
    input.accept = accept;
    input.multiple = false;
    input.onchange = async (event) => {
      const file = (event.target as HTMLInputElement).files?.[0];
      if (!file) return;

      try {
        const data = await uploadFile(file);
        setAttachments((prev) => ({ ...prev, [key]: data }));
        toast('success', 'Attachment uploaded', `${data.filename} is ready.`);
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Attachment upload failed';
        toast('error', 'Attachment upload failed', message);
      }
    };
    input.click();
  }, [ensureAuthenticated, toast]);

  const submitJob = useCallback(async () => {
    if (!ensureAuthenticated()) {
      return;
    }

    const isHtmlUrlMode = tool.id === 'html2pdf' && (getFieldValue('f-html-source') || 'file') === 'url';

    if (!primaryFile && !isHtmlUrlMode) {
      toast('error', 'No file', 'Please upload a file first.');
      return;
    }

    if (tool.id === 'merge' && extraFiles.length === 0) {
      toast('error', 'More PDFs required', 'Merge PDF needs at least two PDF files. Add one more file before processing.');
      return;
    }

    if (tool.id === 'compare' && extraFiles.length === 0 && !getFieldValue('f-file-b')) {
      toast('error', 'Second file required', 'Upload the comparison PDF or paste its file ID before processing.');
      return;
    }

    if (tool.id === 'html2pdf' && isHtmlUrlMode && !getFieldValue('f-html-url')) {
      toast('error', 'URL required', 'Enter a public URL or switch back to uploaded HTML mode.');
      return;
    }

    setProcessing(true);
    setShowJob(true);
    setJobResult(null);
    setJobStatus('pending');
    setJobLabel('Submitting job...');
    setJobProgress(0);

    const payload = buildPayload(tool.id, primaryFile?.file_id ?? null, extraFiles.map((file) => file.file_id), attachments);
    const endpoint = EP[tool.id] ?? '';

    try {
      const { job_id } = await apiSubmitJob(endpoint, payload);
      await refreshUser();
      setJobId(job_id);
      setJobLabel('Job queued - waiting for worker...');
      setJobProgress(5);

      startPoll(job_id, {
        onStatus: (status, label, progress) => {
          setJobStatus(status);
          setJobLabel(label);
          setJobProgress(progress);
        },
        onCompleted: (data) => {
          setJobResult(data);
          setJobStatus('completed');
          setJobLabel('Processing complete - ready to download!');
          setJobProgress(100);
          toast('success', 'Done!', 'Your file is ready to download.');
          setProcessing(false);
        },
        onFailed: (error) => {
          setJobStatus('failed');
          setJobLabel('Job failed.');
          toast('error', 'Job failed', error);
          setProcessing(false);
        },
        onError: (error) => {
          toast('error', 'Polling error', error);
          setProcessing(false);
        },
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Submission failed';
      setJobStatus('failed');
      setJobLabel('Submission failed.');
      toast('error', 'Submission failed', message);
      setProcessing(false);
    }
  }, [attachments, ensureAuthenticated, extraFiles, primaryFile, refreshUser, startPoll, toast, tool.id]);

  const addMoreFiles = useCallback(() => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = tool.accept ?? '.pdf';
    input.multiple = true;
    input.onchange = (event) => {
      const selectedFiles = Array.from((event.target as HTMLInputElement).files ?? []);
      if (selectedFiles.length) selectedFiles.forEach((file) => void doUpload(file, true));
    };
    input.click();
  }, [tool.accept, doUpload]);

  const hasMultiAdd = tool.multi && files.some((file) => file.state.status === 'done');

  return (
    <div id="page-tool">
      <div className="tool-page-wrap">
        <nav className="breadcrumb" aria-label="Breadcrumb">
          <Link href="/">PdfORBIT</Link>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 18l6-6-6-6" />
          </svg>
          <Link href="/tools">Tools</Link>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 18l6-6-6-6" />
          </svg>
          <span>{tool.name}</span>
        </nav>

        <div className="tool-header">
          <div className="tool-header-icon">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.7"
              strokeLinecap="round"
              strokeLinejoin="round"
              width="26"
              height="26"
              dangerouslySetInnerHTML={{ __html: tool.svg }}
            />
          </div>
          <div>
            <h1 className="tool-header-name">{tool.name}</h1>
            <p className="tool-header-desc">{tool.desc}</p>
          </div>
        </div>

        {!showEditor ? (
          <UploadZone
            tool={tool}
            onFiles={handleFiles}
            isDragOver={isDragOver}
            onDragOver={() => setIsDragOver(true)}
            onDragLeave={() => setIsDragOver(false)}
          />
        ) : null}

        <div id="upload-area">
          {files.map((entry) => (
            <FileCard key={entry.id} id={entry.id} state={entry.state} />
          ))}
          {hasMultiAdd ? (
            <button className="multi-add" onClick={addMoreFiles}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              Add more files
            </button>
          ) : null}
        </div>

        {!showEditor && showOptions ? (
          <ToolOptions
            toolId={tool.id}
            formRef={formRef}
            attachments={attachments}
            onSelectAttachment={selectAttachment}
          />
        ) : null}

        {!showEditor && showOptions ? (
          <div className="process-bar">
            <button className="process-btn" onClick={submitJob} disabled={processing}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
              {processing ? 'Processing...' : 'Process'}
            </button>
            <button className="reset-link" onClick={resetTool}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="13" height="13">
                <polyline points="1 4 1 10 7 10" />
                <path d="M3.51 15a9 9 0 102.13-9.36L1 10" />
              </svg>
              Reset
            </button>
          </div>
        ) : null}

        {showEditor && primaryFile && editorPreviewUrl ? (
          <div
            style={{
              position: 'fixed',
              inset: 0,
              zIndex: 80,
              width: '100vw',
              height: '100dvh',
              background: '#000',
            }}
          >
            <PdfEditor
              fileId={primaryFile.file_id}
              fileName={primaryFile.filename}
              pdfUrl={editorPreviewUrl}
              apiBase={`${API_BASE}/api/v1`}
              onClose={resetTool}
            />
          </div>
        ) : null}

        {!showEditor && showJob && jobId ? (
          <JobStatusComponent
            jobId={jobId}
            status={jobStatus}
            label={jobLabel}
            progress={jobProgress}
            result={jobResult}
          />
        ) : null}

        <ToolFaqSection tool={tool} />

        <div className="prose-section">
          <h2>Continue in the tool directory</h2>
          <p>
            Explore adjacent workflows in the <Link href="/tools">PdfORBIT tool directory</Link> or switch directly to related utilities such as{' '}
            <Link href={getToolPathById('compress')}>Compress PDF</Link> and <Link href={getToolPathById('merge')}>Merge PDF</Link>.
          </p>
        </div>
      </div>
    </div>
  );
}