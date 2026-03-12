import { useRef } from 'react';
import type { Tool } from '@/data/tools';

interface UploadZoneProps {
  tool: Tool;
  onFiles: (files: File[]) => void;
  isDragOver: boolean;
  onDragOver: () => void;
  onDragLeave: () => void;
}

export default function UploadZone({ tool, onFiles, isDragOver, onDragOver, onDragLeave }: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const trigger = (e: React.MouseEvent | React.KeyboardEvent) => {
    if (e.type === 'keydown') {
      const ke = e as React.KeyboardEvent;
      if (ke.key !== 'Enter' && ke.key !== ' ') return;
    }
    if ('stopPropagation' in e) (e as React.MouseEvent).stopPropagation();
    if (inputRef.current) {
      inputRef.current.value = '';
      inputRef.current.click();
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    onDragOver();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    onDragLeave();
    const files = Array.from(e.dataTransfer.files);
    if (files.length) onFiles(files);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (files.length) onFiles(files);
  };

  const fileLabel = tool.multi ? 'Files' : tool.accept?.includes('pdf') && !tool.accept?.includes('jpg') ? 'PDF' : 'File';
  const formatsDisplay = (tool.accept ?? '.pdf').toUpperCase().replace(/\./g, '').split(',').join(', ');

  return (
    <>
      <div
        className={`upload-zone${isDragOver ? ' drag-over' : ''}`}
        role="button"
        tabIndex={0}
        aria-label="Upload file"
        onClick={trigger}
        onKeyDown={trigger}
        onDragOver={handleDragOver}
        onDragLeave={onDragLeave}
        onDrop={handleDrop}
      >
        <div className="upload-zone-icon" aria-hidden="true">
          <div className="uz-ring"/>
          <div className="uz-inner">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
              <path d="M12 15V3m0 0L8 7m4-4 4 4"/>
              <path d="M20.39 18.39A5 5 0 0018 9h-1.26A8 8 0 103 16.3"/>
            </svg>
          </div>
        </div>
        <h3>{tool.multi ? 'Select Files' : 'Select File'}</h3>
        <p>or drop it here</p>
        <button
          className="btn btn-red"
          onClick={(e) => { e.stopPropagation(); if (inputRef.current) { inputRef.current.value = ''; inputRef.current.click(); } }}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          Select {fileLabel}
        </button>
        <div className="uz-formats">
          Supported: <b>{formatsDisplay}</b>
        </div>
      </div>
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept={tool.accept}
        multiple={tool.multi}
        onChange={handleChange}
      />
    </>
  );
}
