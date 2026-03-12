/**
 * PdfToolbar.tsx — Primary editing toolbar for the PdfORBIT PDF Editor
 * =====================================================================
 * Renders two rows of tool groups:
 *   Row 1 (editing tools): select · text · highlight · draw · image · signature
 *                          rect · circle · line · eraser · pan
 *   Row 2 (page actions):  rotate-left · rotate-right · delete-page · undo · redo
 *                          zoom controls · apply button
 *
 * Design:
 *   - Toolbar items receive keyboard shortcuts (displayed in tooltips)
 *   - Active tool is highlighted with an accent ring
 *   - Disabled states applied when no document is loaded
 *   - Uses Tailwind utility classes only (no external CSS modules)
 */

"use client";

import React, { useCallback, useEffect } from "react";
import type {
  EditorTool,
  PageRotateAngle,
} from "../../../types/editorTypes";

// ─── Icon primitives (pure SVG, no icon library dependency) ──────────────────

type IconGlyph = string | React.ReactNode;

const Icon: React.FC<{ glyph: IconGlyph; size?: number }> = ({ glyph, size = 18 }) => (
  <svg
    viewBox="0 0 24 24"
    width={size}
    height={size}
    fill="none"
    stroke="currentColor"
    strokeWidth={1.75}
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {typeof glyph === "string" ? <path d={glyph} /> : glyph}
  </svg>
);

const Icons = {
  select: "M5 3l14 9-7 2-4 7L5 3z",
  editText: (
    <>
      <path d="M4 6h10" />
      <path d="M4 10h8" />
      <path d="M4 14h9" />
      <path d="M4 18h6" />
      <path d="M15 19l5-5" />
      <path d="M16 8.5l2.5-2.5a1.414 1.414 0 012 2L18 10.5" />
    </>
  ),
  text: (
    <>
      <path d="M5 6h14" />
      <path d="M12 6v12" />
      <path d="M8 18h8" />
    </>
  ),
  highlight: (
    <>
      <path d="M6 15l5 5 7-7-5-5-7 7z" />
      <path d="M4 20h8" />
      <path d="M14 6l4 4" />
    </>
  ),
  draw: (
    <>
      <path d="M4 20h6" />
      <path d="M14.5 4.5a2.121 2.121 0 013 3L8 17l-4 1 1-4 9.5-9.5z" />
    </>
  ),
  image: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="2" ry="2" />
      <circle cx="8.5" cy="10" r="1.5" />
      <path d="M4 17l5-5 3.5 3.5L15 13l5 4" />
    </>
  ),
  signature: (
    <>
      <path d="M3 16c2.5-2.8 4.4-4.2 5.6-4.2 1.2 0 1.8.7 1.8 1.7 0 1.4-1.1 2.7-2.1 2.7-.7 0-1.1-.4-1.1-1 0-1.4 1.8-3.7 4.2-3.7 1.7 0 2.8 1 4.4 3.2.9 1.2 1.6 1.7 2.2 1.7.7 0 1.4-.4 2-1.2" />
      <path d="M3 20h18" />
    </>
  ),
  rect: "M3 5a2 2 0 012-2h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5z",
  circle: "M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z",
  line: "M5 19L19 5",
  eraser: "M20 20H7L3 16l10-10 7 7-3 3M6 17l4-4",
  pan: (
    <>
      <path d="M9 11V6a1 1 0 112 0v4" />
      <path d="M11 10V5a1 1 0 112 0v5" />
      <path d="M13 10V6a1 1 0 112 0v6" />
      <path d="M15 11V8a1 1 0 112 0v7a4 4 0 01-4 4h-1.5a4.5 4.5 0 01-3.8-2.1L6 14.5a1.2 1.2 0 011.9-1.5L9 14" />
    </>
  ),
  rotateCCW: "M3 12a9 9 0 109 9M3 3v9h9",
  rotateCW:  "M21 12a9 9 0 11-9 9M21 3v9h-9",
  trash:     "M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6",
  undo:      "M3 7v6h6M3.5 13A9 9 0 1021 12",
  redo:      "M21 7v6h-6M20.5 13A9 9 0 113 12",
  zoomIn:    "M11 19a8 8 0 100-16 8 8 0 000 16zM21 21l-4.35-4.35M11 8v6M8 11h6",
  zoomOut:   "M11 19a8 8 0 100-16 8 8 0 000 16zM21 21l-4.35-4.35M8 11h6",
  zoomReset: "M11 19a8 8 0 100-16 8 8 0 000 16zM21 21l-4.35-4.35",
  apply:     "M20 6L9 17l-5-5",
  download:  "M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3",
};

// ─── Types ────────────────────────────────────────────────────────────────────

export interface PdfToolbarProps {
  activeTool: EditorTool;
  onToolChange: (tool: EditorTool) => void;
  onRotatePage: (angle: PageRotateAngle) => void;
  onDeletePage: () => void;
  onUndo: () => void;
  onRedo: () => void;
  onApply: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onZoomReset: () => void;
  onZoomChange: (zoom: number) => void;
  undoDisabled: boolean;
  redoDisabled: boolean;
  applyDisabled: boolean;
  isApplying: boolean;
  currentZoom: number;
  currentPage: number;
  totalPages: number;
  canDeletePage: boolean;
  onClose?: () => void;
}

const MIN_ZOOM = 0.25;
const MAX_ZOOM = 4;

// ─── Sub-components ───────────────────────────────────────────────────────────

interface ToolButtonProps {
  tool?: EditorTool;
  icon: IconGlyph;
  label: string;
  shortcut?: string;
  active?: boolean;
  disabled?: boolean;
  danger?: boolean;
  accent?: boolean;
  onClick: () => void;
}

const ToolButton: React.FC<ToolButtonProps> = ({
  icon,
  label,
  shortcut,
  active = false,
  disabled = false,
  danger = false,
  accent = false,
  onClick,
}) => {
  const base =
    "relative group flex items-center justify-center w-9 h-9 rounded-lg transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 select-none";
  const stateClasses = disabled
    ? "opacity-25 cursor-not-allowed text-zinc-600"
    : active
    ? "bg-red-600/20 text-red-400 border border-red-500/60 shadow-[0_0_12px_rgba(255,0,60,0.4)]"
    : danger
    ? "text-red-500 hover:bg-red-950/40 hover:shadow-[0_0_8px_rgba(255,0,60,0.3)]"
    : accent
    ? "bg-red-600 text-white hover:bg-red-500 shadow-[0_0_16px_rgba(255,0,60,0.5)]"
    : "text-zinc-400 hover:bg-zinc-800 hover:text-red-400";

  return (
    <button
      type="button"
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      aria-label={label}
      aria-pressed={active}
      title={shortcut ? `${label} [${shortcut}]` : label}
      className={`${base} ${stateClasses}`}
    >
      <Icon glyph={icon} size={17} />
      {/* Tooltip */}
      <span
        className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2
                   px-2 py-1 rounded-md text-xs font-medium whitespace-nowrap
                   bg-zinc-900 text-red-400 border border-red-900/50 opacity-0 group-hover:opacity-100
                   group-focus-visible:opacity-100 transition-opacity duration-150 z-50 shadow-[0_0_8px_rgba(255,0,60,0.3)]"
      >
        {label}
        {shortcut && (
          <span className="ml-1.5 opacity-60 font-mono text-[10px]">[{shortcut}]</span>
        )}
      </span>
    </button>
  );
};

const Divider: React.FC = () => (
  <div className="w-px h-7 bg-red-900/30 mx-1 flex-shrink-0" />
);

// ─── Main toolbar component ───────────────────────────────────────────────────

export const PdfToolbar: React.FC<PdfToolbarProps> = ({
  activeTool,
  onToolChange,
  onRotatePage,
  onDeletePage,
  onUndo,
  onRedo,
  onApply,
  onZoomIn,
  onZoomOut,
  onZoomReset,
  onZoomChange,
  undoDisabled,
  redoDisabled,
  applyDisabled,
  isApplying,
  currentZoom,
  currentPage,
  totalPages,
  canDeletePage,
  onClose,
}) => {
  // ── Keyboard shortcut handler ──────────────────────────────────────────────
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Do not fire if focus is inside an input/textarea
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") return;

      const ctrl = e.ctrlKey || e.metaKey;

      if (ctrl && e.key === "z" && !e.shiftKey) {
        e.preventDefault();
        if (!undoDisabled) onUndo();
      } else if (ctrl && (e.key === "y" || (e.key === "z" && e.shiftKey))) {
        e.preventDefault();
        if (!redoDisabled) onRedo();
      } else if (e.key === "v" || e.key === "V") {
        onToolChange("select");
      } else if (e.key === "x" || e.key === "X") {
        onToolChange("edit-text");
      } else if (e.key === "t" || e.key === "T") {
        onToolChange("text");
      } else if (e.key === "h" || e.key === "H") {
        onToolChange("highlight");
      } else if (e.key === "d" || e.key === "D") {
        onToolChange("draw");
      } else if (e.key === "r" || e.key === "R") {
        onToolChange("rect");
      } else if (e.key === "c" || e.key === "C") {
        onToolChange("circle");
      } else if (e.key === "e" || e.key === "E") {
        onToolChange("eraser");
      } else if (e.key === "Escape") {
        onToolChange("select");
      } else if (e.key === "Delete" || e.key === "Backspace") {
        // handled by canvas layer; do not intercept here
      }
    },
    [activeTool, undoDisabled, redoDisabled, onUndo, onRedo, onToolChange]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  const isActive = (t: EditorTool) => activeTool === t;

  return (
    <div
      className="flex-shrink-0 sticky top-0 z-40 w-full min-w-0 overflow-x-auto bg-zinc-950
             border-b border-red-900/40 select-none"
      style={{ boxShadow: "0 1px 0 0 rgba(255,0,60,0.15), 0 4px 24px 0 rgba(255,0,60,0.05)" }}
      role="toolbar"
      aria-label="PDF editor toolbar"
    >
      <div className="flex min-w-[900px] flex-col gap-0">
      {/* ── Row 1: Editing tools ─────────────────────────────────────────── */}
      <div className="flex items-center gap-0.5 px-3 py-1.5 w-full min-w-max">
        {/* Selection */}
        <ToolButton
          icon={Icons.select}
          label="Select"
          shortcut="V"
          active={isActive("select")}
          onClick={() => onToolChange("select")}
        />
        <ToolButton
          icon={Icons.editText}
          label="Edit Existing Text"
          shortcut="X"
          active={isActive("edit-text")}
          onClick={() => onToolChange("edit-text")}
        />

        <Divider />

        {/* Text */}
        <ToolButton
          icon={Icons.text}
          label="Text Box"
          shortcut="T"
          active={isActive("text")}
          onClick={() => onToolChange("text")}
        />

        {/* Highlight */}
        <ToolButton
          icon={Icons.highlight}
          label="Highlight"
          shortcut="H"
          active={isActive("highlight")}
          onClick={() => onToolChange("highlight")}
        />

        <Divider />

        {/* Draw */}
        <ToolButton
          icon={Icons.draw}
          label="Pen / Draw"
          shortcut="D"
          active={isActive("draw")}
          onClick={() => onToolChange("draw")}
        />

        {/* Image */}
        <ToolButton
          icon={Icons.image}
          label="Insert Image"
          shortcut="I"
          active={isActive("image")}
          onClick={() => onToolChange("image")}
        />

        {/* Signature */}
        <ToolButton
          icon={Icons.signature}
          label="Signature"
          shortcut="S"
          active={isActive("signature")}
          onClick={() => onToolChange("signature")}
        />

        <Divider />

        {/* Shapes */}
        <ToolButton
          icon={Icons.rect}
          label="Rectangle"
          shortcut="R"
          active={isActive("rect")}
          onClick={() => onToolChange("rect")}
        />
        <ToolButton
          icon={Icons.circle}
          label="Circle / Ellipse"
          shortcut="C"
          active={isActive("circle")}
          onClick={() => onToolChange("circle")}
        />
        <ToolButton
          icon={Icons.line}
          label="Line"
          active={isActive("line")}
          onClick={() => onToolChange("line")}
        />

        <Divider />

        {/* Utilities */}
        <ToolButton
          icon={Icons.eraser}
          label="Eraser"
          shortcut="E"
          active={isActive("eraser")}
          onClick={() => onToolChange("eraser")}
        />
        <ToolButton
          icon={Icons.pan}
          label="Pan / Hand"
          active={isActive("pan")}
          onClick={() => onToolChange("pan")}
        />

        <Divider />

        {/* Undo / Redo */}
        <ToolButton
          icon={Icons.undo}
          label="Undo"
          shortcut="Ctrl+Z"
          disabled={undoDisabled}
          onClick={onUndo}
        />
        <ToolButton
          icon={Icons.redo}
          label="Redo"
          shortcut="Ctrl+Y"
          disabled={redoDisabled}
          onClick={onRedo}
        />

        <Divider />

        <ToolButton
          icon={Icons.download}
          label="Download Edited PDF"
          accent
          disabled={applyDisabled || isApplying}
          onClick={onApply}
        />

        <div className="flex-1" />

        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="px-3 h-9 rounded-lg text-xs font-semibold tracking-[0.12em] uppercase
                       text-zinc-400 border border-zinc-800 bg-zinc-900/80 hover:text-red-300
                       hover:border-red-500/40 transition-colors focus:outline-none
                       focus-visible:ring-2 focus-visible:ring-red-500"
            aria-label="Exit fullscreen editor"
          >
            Exit
          </button>
        )}
      </div>

      <div className="flex items-center gap-3 px-3 py-2 border-t border-red-900/20 w-full min-w-max">
        <div className="flex items-center gap-0.5">
          <ToolButton
            icon={Icons.zoomOut}
            label="Zoom Out"
            shortcut="-"
            onClick={onZoomOut}
          />
          <button
            type="button"
            onClick={onZoomReset}
            className="px-2.5 h-9 text-xs font-mono font-semibold text-red-400
                       hover:bg-zinc-800 hover:text-red-300 rounded-lg transition-colors
                       focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
            title="Reset zoom (100%)"
          >
            {Math.round(currentZoom * 100)}%
          </button>
          <ToolButton
            icon={Icons.zoomIn}
            label="Zoom In"
            shortcut="+"
            onClick={onZoomIn}
          />
        </div>

        <div className="flex items-center gap-2 min-w-[220px] flex-1 max-w-[360px]">
          <span className="text-[10px] uppercase tracking-[0.18em] text-zinc-500 whitespace-nowrap">
            Zoom
          </span>
          <input
            type="range"
            min={MIN_ZOOM}
            max={MAX_ZOOM}
            step={0.01}
            value={currentZoom}
            onChange={(event) => onZoomChange(parseFloat(event.target.value))}
            className="flex-1 h-1.5 rounded-full appearance-none bg-zinc-800
                       [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4
                       [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full
                       [&::-webkit-slider-thumb]:bg-red-500 [&::-webkit-slider-thumb]:cursor-pointer
                       [&::-webkit-slider-thumb]:shadow-[0_0_10px_rgba(255,0,60,0.8)]"
            aria-label="Zoom slider"
          />
          <span className="text-[11px] font-mono tabular-nums text-zinc-400 w-12 text-right">
            {Math.round(currentZoom * 100)}%
          </span>
        </div>

        <Divider />

        {/* Page indicator */}
        <div className="px-2.5 text-xs text-zinc-500 whitespace-nowrap tabular-nums">
          Pg <span className="font-semibold text-red-400">{currentPage}</span>
          {" / "}
          {totalPages}
        </div>

        <Divider />

        {/* Page operations */}
        <ToolButton
          icon={Icons.rotateCCW}
          label="Rotate Page Left (90°)"
          onClick={() => onRotatePage(-90)}
        />
        <ToolButton
          icon={Icons.rotateCW}
          label="Rotate Page Right (90°)"
          onClick={() => onRotatePage(90)}
        />
        <ToolButton
          icon={Icons.trash}
          label="Delete Page"
          disabled={!canDeletePage}
          danger
          onClick={onDeletePage}
        />

        <div className="ml-auto text-[10px] uppercase tracking-[0.18em] text-zinc-600 whitespace-nowrap">
          {isApplying ? "Applying changes" : "Ctrl + wheel to zoom • Space + drag to pan"}
        </div>
      </div>
      </div>
    </div>
  );
};

export default PdfToolbar;
