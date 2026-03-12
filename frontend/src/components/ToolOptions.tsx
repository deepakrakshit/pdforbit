import { useState } from 'react';
import type { RefObject } from 'react';

import type { UploadResponse } from '@/lib/api';

type AttachmentKey = 'watermarkImage' | 'signImage' | 'signCert';

interface ToolOptionsProps {
  toolId: string;
  formRef: RefObject<HTMLDivElement>;
  attachments: Record<AttachmentKey, UploadResponse | null>;
  onSelectAttachment: (key: AttachmentKey, accept: string) => void;
}

function FieldRow({ children }: { children: React.ReactNode }) {
  return <div className="form-row">{children}</div>;
}

function Field({ label, children, wide = false }: { label: string; children: React.ReactNode; wide?: boolean }) {
  return (
    <div className="form-field" style={wide ? { gridColumn: '1/-1' } : undefined}>
      <div className="form-label">{label}</div>
      {children}
    </div>
  );
}

function Hint({ children }: { children: React.ReactNode }) {
  return <div className="form-hint">{children}</div>;
}

function Checkbox({ id, label, defaultChecked = false }: { id: string; label: string; defaultChecked?: boolean }) {
  return (
    <label className="form-check" style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
      <input id={id} type="checkbox" defaultChecked={defaultChecked} />
      <span>{label}</span>
    </label>
  );
}

function AttachmentField({
  label,
  accept,
  attachment,
  onSelect,
  buttonLabel,
  hint,
}: {
  label: string;
  accept: string;
  attachment: UploadResponse | null;
  onSelect: () => void;
  buttonLabel: string;
  hint?: string;
}) {
  return (
    <Field label={label} wide>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <button type="button" className="btn btn-red" onClick={onSelect}>
          {buttonLabel}
        </button>
        <div className="form-info" style={{ margin: 0 }}>
          {attachment ? `${attachment.filename} uploaded` : `Accepted: ${accept.replace(/\./g, '').toUpperCase()}`}
        </div>
      </div>
      {hint ? <Hint>{hint}</Hint> : null}
    </Field>
  );
}

function outField(def = 'output.pdf', label = 'Output Filename') {
  return (
    <FieldRow>
      <Field label={label}>
        <input className="form-ctrl" id="f-output" defaultValue={def} />
      </Field>
    </FieldRow>
  );
}

function SplitFields() {
  const [mode, setMode] = useState('by_range');

  return (
    <>
      <FieldRow>
        <Field label="Split Mode">
          <select className="form-ctrl" id="f-mode" value={mode} onChange={(event) => setMode(event.target.value)}>
            <option value="by_range">By page range</option>
            <option value="every_n_pages">Every N pages</option>
            <option value="by_bookmark">By top-level bookmark</option>
          </select>
        </Field>
        <Field label="Output Prefix">
          <input className="form-ctrl" id="f-output-prefix" defaultValue="part" />
        </Field>
      </FieldRow>

      {mode === 'by_range' ? (
        <FieldRow>
          <Field label="Page Ranges" wide>
            <input className="form-ctrl" id="f-ranges" placeholder="1-3, 5, 9-12" />
            <Hint>Each range becomes a separate PDF. One range returns a direct PDF; multiple ranges return a ZIP.</Hint>
          </Field>
        </FieldRow>
      ) : null}

      {mode === 'every_n_pages' ? (
        <FieldRow>
          <Field label="Pages Per Part">
            <input className="form-ctrl" id="f-every-n" type="number" defaultValue="5" min="1" />
          </Field>
        </FieldRow>
      ) : null}

      {mode === 'by_bookmark' ? (
        <div className="form-info">Each top-level bookmark becomes its own PDF, using the bookmark title as the part name.</div>
      ) : null}
    </>
  );
}

function HtmlFields() {
  const [sourceMode, setSourceMode] = useState<'file' | 'url'>('file');

  return (
    <>
      <FieldRow>
        <Field label="HTML Source">
          <select
            className="form-ctrl"
            id="f-html-source"
            value={sourceMode}
            onChange={(event) => setSourceMode(event.target.value as 'file' | 'url')}
          >
            <option value="file">Uploaded HTML file</option>
            <option value="url">Public URL</option>
          </select>
        </Field>
        <Field label="Page Size">
          <select className="form-ctrl" id="f-pagesize" defaultValue="A4">
            <option value="A4">A4</option>
            <option value="A3">A3</option>
            <option value="Letter">Letter</option>
            <option value="Legal">Legal</option>
          </select>
        </Field>
      </FieldRow>

      {sourceMode === 'url' ? (
        <FieldRow>
          <Field label="Public URL" wide>
            <input className="form-ctrl" id="f-html-url" placeholder="https://example.com/report" />
            <Hint>Only publicly reachable HTTP or HTTPS URLs are allowed. Private and internal addresses are blocked.</Hint>
          </Field>
        </FieldRow>
      ) : (
        <div className="form-info">Upload an `.html` or `.htm` file above, or switch to URL mode to fetch a public webpage directly.</div>
      )}

      {outField('webpage.pdf')}
    </>
  );
}

function CropFields() {
  return (
    <>
      <div className="form-info">Crop values use PDF points. Leave coordinates blank and enable auto-crop to trim whitespace automatically.</div>
      <FieldRow>
        <Field label="Pages (blank = all)">
          <input className="form-ctrl" id="f-pages" placeholder="1, 3, 5-8" />
        </Field>
        <Field label="Options" wide>
          <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap' }}>
            <Checkbox id="f-auto-crop" label="Auto-crop whitespace" />
            <Checkbox id="f-permanent-crop" label="Apply permanent crop" />
          </div>
        </Field>
      </FieldRow>
      <FieldRow>
        <Field label="Left (pt)">
          <input className="form-ctrl" id="f-left" type="number" defaultValue="50" />
        </Field>
        <Field label="Bottom (pt)">
          <input className="form-ctrl" id="f-bottom" type="number" defaultValue="50" />
        </Field>
        <Field label="Right (pt)">
          <input className="form-ctrl" id="f-right" type="number" defaultValue="545" />
        </Field>
        <Field label="Top (pt)">
          <input className="form-ctrl" id="f-top" type="number" defaultValue="792" />
        </Field>
      </FieldRow>
      {outField('cropped.pdf')}
    </>
  );
}

function SignFields({ attachments, onSelectAttachment }: Pick<ToolOptionsProps, 'attachments' | 'onSelectAttachment'>) {
  const [useDigitalSignature, setUseDigitalSignature] = useState(false);

  return (
    <>
      <FieldRow>
        <Field label="Signature Text" wide>
          <input className="form-ctrl" id="f-sigtext" placeholder="Jane Doe, CEO" />
        </Field>
      </FieldRow>

      <FieldRow>
        <Field label="Page">
          <input className="form-ctrl" id="f-page" type="number" defaultValue="1" min="1" />
        </Field>
        <Field label="X (pt)">
          <input className="form-ctrl" id="f-x" type="number" defaultValue="60" />
        </Field>
        <Field label="Y (pt)">
          <input className="form-ctrl" id="f-y" type="number" defaultValue="700" />
        </Field>
        <Field label="Width (pt)">
          <input className="form-ctrl" id="f-width" type="number" defaultValue="200" />
        </Field>
        <Field label="Height (pt)">
          <input className="form-ctrl" id="f-height" type="number" defaultValue="80" />
        </Field>
      </FieldRow>

      <FieldRow>
        <Field label="Border Style">
          <select className="form-ctrl" id="f-sign-border" defaultValue="box">
            <option value="box">Box</option>
            <option value="underline">Underline</option>
            <option value="none">No border</option>
          </select>
        </Field>
        <Field label="Signature Options" wide>
          <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap' }}>
            <label className="form-check" style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <input
                id="f-sign-digital"
                type="checkbox"
                checked={useDigitalSignature}
                onChange={(event) => setUseDigitalSignature(event.target.checked)}
              />
              <span>Use PKCS#12 digital signature</span>
            </label>
            <Checkbox id="f-sign-timestamp" label="Include timestamp" defaultChecked />
          </div>
        </Field>
      </FieldRow>

      <AttachmentField
        label="Signature Image Upload"
        accept=".png,.jpg,.jpeg,.webp"
        attachment={attachments.signImage}
        onSelect={() => onSelectAttachment('signImage', '.png,.jpg,.jpeg,.webp')}
        buttonLabel="Upload signature image"
        hint="Optional. If provided, the uploaded signature image is stamped into the signature box."
      />

      {useDigitalSignature ? (
        <>
          <AttachmentField
            label="Certificate Upload"
            accept=".p12,.pfx"
            attachment={attachments.signCert}
            onSelect={() => onSelectAttachment('signCert', '.p12,.pfx')}
            buttonLabel="Upload certificate"
            hint="Upload a PKCS#12 certificate. If signing fails, the backend falls back to a visual signature stamp."
          />
          <FieldRow>
            <Field label="Certificate Password">
              <input className="form-ctrl" id="f-sign-cert-password" type="password" autoComplete="new-password" />
            </Field>
          </FieldRow>
        </>
      ) : null}

      {outField('signed.pdf')}
    </>
  );
}

function WatermarkFields({ attachments, onSelectAttachment }: Pick<ToolOptionsProps, 'attachments' | 'onSelectAttachment'>) {
  return (
    <>
      <FieldRow>
        <Field label="Watermark Text" wide>
          <input className="form-ctrl" id="f-text" defaultValue="CONFIDENTIAL" />
        </Field>
      </FieldRow>
      <FieldRow>
        <Field label="Position">
          <select className="form-ctrl" id="f-position" defaultValue="diagonal">
            <option value="diagonal">Diagonal</option>
            <option value="center">Center</option>
            <option value="top_left">Top left</option>
            <option value="top_center">Top center</option>
            <option value="top_right">Top right</option>
            <option value="bottom_left">Bottom left</option>
            <option value="bottom_center">Bottom center</option>
            <option value="bottom_right">Bottom right</option>
          </select>
        </Field>
        <Field label="Opacity">
          <input className="form-ctrl" id="f-opacity" type="number" defaultValue="0.3" min="0" max="1" step="0.05" />
        </Field>
        <Field label="Font Size">
          <input className="form-ctrl" id="f-fontsize" type="number" defaultValue="72" />
        </Field>
        <Field label="Rotation (deg)">
          <input className="form-ctrl" id="f-rotation" type="number" defaultValue="45" min="-360" max="360" />
        </Field>
      </FieldRow>
      <FieldRow>
        <Field label="Color">
          <input className="form-ctrl" id="f-watermark-color" defaultValue="#000000" />
        </Field>
        <Field label="Font Family">
          <input className="form-ctrl" id="f-watermark-font" placeholder="helv" />
        </Field>
        <Field label="Skip Pages">
          <input className="form-ctrl" id="f-watermark-skip-pages" placeholder="1, 5, 9" />
        </Field>
        <Field label="Apply Only To First Page">
          <Checkbox id="f-watermark-first-page-only" label="First page only" />
        </Field>
      </FieldRow>
      <AttachmentField
        label="Overlay Image Upload"
        accept=".png,.jpg,.jpeg,.webp"
        attachment={attachments.watermarkImage}
        onSelect={() => onSelectAttachment('watermarkImage', '.png,.jpg,.jpeg,.webp')}
        buttonLabel="Upload watermark image"
        hint="Optional. Upload an image if you want a visual watermark overlay in addition to, or instead of, text."
      />
      {outField('watermarked.pdf')}
    </>
  );
}

export default function ToolOptions({ toolId, formRef, attachments, onSelectAttachment }: ToolOptionsProps) {
  const renderForm = () => {
    switch (toolId) {
      case 'merge':
        return (
          <>
            <div className="form-info">The first uploaded PDF stays first. Add more files above and they will be merged in upload order.</div>
            {outField('merged.pdf')}
          </>
        );

      case 'split':
        return <SplitFields />;

      case 'extract':
        return (
          <>
            <FieldRow>
              <Field label="Pages to Extract" wide>
                <input className="form-ctrl" id="f-pages" placeholder="1, 3, 5-8" />
                <Hint>Use comma-separated page numbers or ranges.</Hint>
              </Field>
            </FieldRow>
            {outField('extracted.pdf')}
          </>
        );

      case 'remove':
        return (
          <>
            <FieldRow>
              <Field label="Pages to Remove" wide>
                <input className="form-ctrl" id="f-pages" placeholder="2, 4, 6" />
                <Hint>All other pages stay in the result PDF.</Hint>
              </Field>
            </FieldRow>
            {outField('modified.pdf')}
          </>
        );

      case 'reorder':
        return (
          <>
            <FieldRow>
              <Field label="New Page Order" wide>
                <input className="form-ctrl" id="f-order" placeholder="3, 1, 2, 5, 4" />
                <Hint>Use each page once. Duplicate page numbers are rejected.</Hint>
              </Field>
            </FieldRow>
            {outField('reordered.pdf')}
          </>
        );

      case 'compress':
        return (
          <>
            <FieldRow>
              <Field label="Compression Level">
                <select className="form-ctrl" id="f-level" defaultValue="medium">
                  <option value="low">Maximum compression</option>
                  <option value="medium">Balanced</option>
                  <option value="high">Highest quality</option>
                </select>
              </Field>
            </FieldRow>
            {outField('compressed.pdf')}
          </>
        );

      case 'repair':
        return (
          <>
            <div className="form-info">PdfORBIT rebuilds the file structure and rewrites the PDF if recovery succeeds.</div>
            {outField('repaired.pdf')}
          </>
        );

      case 'ocr':
        return (
          <>
            <FieldRow>
              <Field label="Document Language">
                <select className="form-ctrl" id="f-lang" defaultValue="eng">
                  <option value="eng">English</option>
                  <option value="fra">French</option>
                  <option value="deu">German</option>
                  <option value="spa">Spanish</option>
                  <option value="ita">Italian</option>
                  <option value="por">Portuguese</option>
                  <option value="chi_sim">Chinese (Simplified)</option>
                  <option value="jpn">Japanese</option>
                  <option value="kor">Korean</option>
                  <option value="ara">Arabic</option>
                </select>
              </Field>
              <Field label="Scan DPI">
                <select className="form-ctrl" id="f-dpi" defaultValue="300">
                  <option value="150">150</option>
                  <option value="300">300</option>
                  <option value="600">600</option>
                </select>
              </Field>
            </FieldRow>
            {outField('searchable.pdf')}
          </>
        );

      case 'img2pdf':
        return (
          <>
            <div className="form-info">Upload one or more images above. Multiple images are converted into a multi-page PDF in upload order.</div>
            <FieldRow>
              <Field label="Render DPI">
                <select className="form-ctrl" id="f-dpi" defaultValue="300">
                  <option value="150">150</option>
                  <option value="300">300</option>
                  <option value="600">600</option>
                </select>
              </Field>
              <Field label="Page Size">
                <select className="form-ctrl" id="f-convert-pagesize" defaultValue="original">
                  <option value="original">Original image size</option>
                  <option value="fit">Fit to page</option>
                  <option value="A4">A4</option>
                  <option value="A3">A3</option>
                  <option value="Letter">Letter</option>
                  <option value="Legal">Legal</option>
                </select>
              </Field>
            </FieldRow>
            {outField('images.pdf')}
          </>
        );

      case 'word2pdf':
        return outField('document.pdf');

      case 'excel2pdf':
        return outField('spreadsheet.pdf');

      case 'ppt2pdf':
        return (
          <>
            <FieldRow>
              <Field label="Fallback Options" wide>
                <Checkbox id="f-include-speaker-notes" label="Include speaker notes if fallback rendering is used" />
              </Field>
            </FieldRow>
            {outField('presentation.pdf')}
          </>
        );

      case 'html2pdf':
        return <HtmlFields />;

      case 'pdf2img':
        return (
          <>
            <FieldRow>
              <Field label="Image Format">
                <select className="form-ctrl" id="f-fmt" defaultValue="jpg">
                  <option value="jpg">JPG</option>
                  <option value="jpeg">JPEG</option>
                  <option value="png">PNG</option>
                  <option value="webp">WEBP</option>
                </select>
              </Field>
              <Field label="Resolution (DPI)">
                <select className="form-ctrl" id="f-dpi" defaultValue="150">
                  <option value="72">72</option>
                  <option value="150">150</option>
                  <option value="300">300</option>
                  <option value="600">600</option>
                </select>
              </Field>
              <Field label="Quality (1-100)">
                <input className="form-ctrl" id="f-quality" type="number" defaultValue="85" min="1" max="100" />
              </Field>
            </FieldRow>
            <FieldRow>
              <Field label="Single Page (optional)">
                <input className="form-ctrl" id="f-single-page" type="number" min="1" placeholder="Leave blank for all pages" />
              </Field>
              <Field label="Thumbnail Mode">
                <Checkbox id="f-thumbnail" label="Generate thumbnail" />
              </Field>
              <Field label="Thumbnail Max Size (px)">
                <input className="form-ctrl" id="f-thumbnail-max" type="number" defaultValue="512" min="32" max="4096" />
              </Field>
            </FieldRow>
            <div className="form-hint">All pages return a ZIP. Single-page export returns the direct image file.</div>
          </>
        );

      case 'pdf2word':
        return (
          <>
            <div className="form-info">Exports the PDF into editable DOCX. Complex layouts may still need cleanup after conversion.</div>
            {outField('converted.docx')}
          </>
        );

      case 'pdf2excel':
        return (
          <>
            <div className="form-info">Extracts detected tables into XLSX. Pages without clear tables fall back to plain text sheets.</div>
            {outField('converted.xlsx')}
          </>
        );

      case 'pdf2ppt':
        return (
          <>
            <div className="form-info">Converts PDF pages into PPTX slides. Speaker notes are included when available in fallback mode.</div>
            {outField('converted.pptx')}
          </>
        );

      case 'pdf2pdfa':
        return (
          <>
            <FieldRow>
              <Field label="PDF/A Level">
                <select className="form-ctrl" id="f-pdfa" defaultValue="1b">
                  <option value="1b">PDF/A-1b</option>
                  <option value="2b">PDF/A-2b</option>
                  <option value="3b">PDF/A-3b</option>
                </select>
                <Hint>Choose the archival conformance level that matches your retention requirement.</Hint>
              </Field>
            </FieldRow>
            {outField('archived.pdf')}
          </>
        );

      case 'rotate':
        return (
          <>
            <FieldRow>
              <Field label="Rotation Angle">
                <select className="form-ctrl" id="f-angle" defaultValue="90">
                  <option value="90">90 degrees clockwise</option>
                  <option value="180">180 degrees</option>
                  <option value="270">90 degrees counter-clockwise</option>
                </select>
              </Field>
              <Field label="Pages (blank = all)">
                <input className="form-ctrl" id="f-pages" placeholder="1, 3, 5" />
              </Field>
              <Field label="Rotation Mode">
                <Checkbox id="f-rotate-relative" label="Add to current rotation" defaultChecked />
              </Field>
            </FieldRow>
            {outField('rotated.pdf')}
          </>
        );

      case 'watermark':
        return <WatermarkFields attachments={attachments} onSelectAttachment={onSelectAttachment} />;

      case 'pagenums':
        return (
          <>
            <FieldRow>
              <Field label="Position">
                <select className="form-ctrl" id="f-position" defaultValue="bottom_center">
                  <option value="bottom_center">Bottom center</option>
                  <option value="bottom_left">Bottom left</option>
                  <option value="bottom_right">Bottom right</option>
                  <option value="top_center">Top center</option>
                  <option value="top_left">Top left</option>
                  <option value="top_right">Top right</option>
                </select>
              </Field>
              <Field label="Start Number">
                <input className="form-ctrl" id="f-start" type="number" defaultValue="1" min="1" />
              </Field>
              <Field label="Font Size">
                <input className="form-ctrl" id="f-fontsize" type="number" defaultValue="12" min="6" max="72" />
              </Field>
              <Field label="Color">
                <input className="form-ctrl" id="f-color" defaultValue="#000000" />
              </Field>
            </FieldRow>
            <FieldRow>
              <Field label="Prefix">
                <input className="form-ctrl" id="f-prefix" placeholder="Page " />
              </Field>
              <Field label="Suffix">
                <input className="form-ctrl" id="f-suffix" placeholder="" />
              </Field>
              <Field label="Font Family">
                <input className="form-ctrl" id="f-pagenums-font" placeholder="helv" />
              </Field>
              <Field label="Numbering Style">
                <select className="form-ctrl" id="f-numbering-style" defaultValue="arabic">
                  <option value="arabic">Arabic</option>
                  <option value="roman_lower">Roman lower</option>
                  <option value="roman_upper">Roman upper</option>
                  <option value="alpha_lower">Alphabetic lower</option>
                  <option value="alpha_upper">Alphabetic upper</option>
                </select>
              </Field>
            </FieldRow>
            <FieldRow>
              <Field label="Skip First N Pages">
                <input className="form-ctrl" id="f-skip-first" type="number" defaultValue="0" min="0" />
              </Field>
              <Field label="Skip Last N Pages">
                <input className="form-ctrl" id="f-skip-last" type="number" defaultValue="0" min="0" />
              </Field>
              <Field label="Appearance">
                <Checkbox id="f-background-box" label="Add background box" />
              </Field>
            </FieldRow>
            {outField('numbered.pdf')}
          </>
        );

      case 'crop':
        return <CropFields />;

      case 'unlock':
        return (
          <>
            <FieldRow>
              <Field label="PDF Password">
                <input className="form-ctrl" id="f-password" type="password" autoComplete="current-password" />
              </Field>
            </FieldRow>
            {outField('unlocked.pdf')}
          </>
        );

      case 'protect':
        return (
          <>
            <FieldRow>
              <Field label="User Password">
                <input className="form-ctrl" id="f-upwd" type="password" autoComplete="new-password" />
              </Field>
              <Field label="Owner Password">
                <input className="form-ctrl" id="f-opwd" type="password" autoComplete="new-password" />
              </Field>
              <Field label="Encryption">
                <select className="form-ctrl" id="f-enc" defaultValue="256">
                  <option value="128">128-bit</option>
                  <option value="256">256-bit</option>
                </select>
              </Field>
            </FieldRow>
            <FieldRow>
              <Field label="Permissions" wide>
                <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap' }}>
                  <Checkbox id="f-allow-printing" label="Allow printing" defaultChecked />
                  <Checkbox id="f-allow-copying" label="Allow copying" defaultChecked />
                  <Checkbox id="f-allow-annotations" label="Allow annotations" defaultChecked />
                  <Checkbox id="f-allow-form-filling" label="Allow form filling" defaultChecked />
                </div>
              </Field>
            </FieldRow>
            {outField('protected.pdf')}
          </>
        );

      case 'sign':
        return <SignFields attachments={attachments} onSelectAttachment={onSelectAttachment} />;

      case 'redact':
        return (
          <>
            <FieldRow>
              <Field label="Keywords" wide>
                <input className="form-ctrl" id="f-keywords" placeholder="John Smith, Confidential, AC-2024-15" />
              </Field>
            </FieldRow>
            <FieldRow>
              <Field label="Regex Patterns" wide>
                <input className="form-ctrl" id="f-regex" placeholder="\\b\\d{3}-\\d{2}-\\d{4}\\b" />
                <Hint>Use safe regex only. Nested quantifiers, lookarounds, and backreferences are blocked.</Hint>
              </Field>
            </FieldRow>
            <FieldRow>
              <Field label="Fill Color">
                <select className="form-ctrl" id="f-rcolor" defaultValue="#000000">
                  <option value="#000000">Black</option>
                  <option value="#FFFFFF">White</option>
                </select>
              </Field>
              <Field label="Mode" wide>
                <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap' }}>
                  <Checkbox id="f-redact-preview" label="Preview mode only" />
                  <Checkbox id="f-redact-whole-word" label="Whole-word keyword matching" />
                </div>
              </Field>
            </FieldRow>
            {outField('redacted.pdf')}
          </>
        );

      case 'compare':
        return (
          <>
            <div className="form-info">Upload the first PDF above, then add the second PDF using the extra file button. You can also paste a second file ID if it was uploaded elsewhere.</div>
            <FieldRow>
              <Field label="Comparison Mode">
                <select className="form-ctrl" id="f-compare-mode" defaultValue="combined">
                  <option value="combined">Combined text and visual diff</option>
                  <option value="text">Text diff only</option>
                  <option value="visual">Visual diff only</option>
                </select>
              </Field>
              <Field label="Second File ID (optional)" wide>
                <input className="form-ctrl" id="f-file-b" placeholder="file_..." />
              </Field>
            </FieldRow>
            {outField('comparison.zip')}
          </>
        );

      case 'translate':
        return (
          <>
            <FieldRow>
              <Field label="Target Language">
                <select className="form-ctrl" id="f-target" defaultValue="en">
                  <option value="en">English</option>
                  <option value="fr">French</option>
                  <option value="de">German</option>
                  <option value="es">Spanish</option>
                  <option value="it">Italian</option>
                  <option value="pt">Portuguese</option>
                  <option value="zh">Chinese</option>
                  <option value="ja">Japanese</option>
                  <option value="ko">Korean</option>
                  <option value="ar">Arabic</option>
                  <option value="ru">Russian</option>
                  <option value="hi">Hindi</option>
                </select>
              </Field>
              <Field label="Source Language">
                <select className="form-ctrl" id="f-source" defaultValue="">
                  <option value="">Auto-detect</option>
                  <option value="en">English</option>
                  <option value="fr">French</option>
                  <option value="de">German</option>
                  <option value="es">Spanish</option>
                  <option value="zh">Chinese</option>
                  <option value="ja">Japanese</option>
                  <option value="ar">Arabic</option>
                </select>
              </Field>
            </FieldRow>
            {outField('translated.pdf')}
          </>
        );

      case 'summarize':
        return (
          <>
            <div className="form-info">Orbit Brief extracts text, falls back to OCR when needed, and generates a structured executive brief.</div>
            <FieldRow>
              <Field label="Output Language">
                <select className="form-ctrl" id="f-summary-lang" defaultValue="en">
                  <option value="en">English</option>
                  <option value="fr">French</option>
                  <option value="de">German</option>
                  <option value="es">Spanish</option>
                  <option value="it">Italian</option>
                  <option value="pt">Portuguese</option>
                  <option value="zh">Chinese</option>
                  <option value="ja">Japanese</option>
                  <option value="ko">Korean</option>
                  <option value="ar">Arabic</option>
                  <option value="ru">Russian</option>
                  <option value="hi">Hindi</option>
                </select>
              </Field>
              <Field label="Brief Length">
                <select className="form-ctrl" id="f-summary-length" defaultValue="medium">
                  <option value="short">Short</option>
                  <option value="medium">Medium</option>
                  <option value="long">Long</option>
                </select>
              </Field>
            </FieldRow>
            <FieldRow>
              <Field label="Focus Area" wide>
                <input className="form-ctrl" id="f-summary-focus" placeholder="risks, revenue, action items, compliance issues" />
              </Field>
            </FieldRow>
            {outField('orbit-brief.pdf')}
          </>
        );

      default:
        return null;
    }
  };

  const content = renderForm();
  if (!content) return null;

  return (
    <div className="options-panel" ref={formRef}>
      <div className="options-title">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
        </svg>
        Configure Options
      </div>
      {content}
    </div>
  );
}