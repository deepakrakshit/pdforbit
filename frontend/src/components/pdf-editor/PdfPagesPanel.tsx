/**
 * PdfPagesPanel.tsx — Page Thumbnail Navigator
 * =============================================
 * Left sidebar that displays all PDF pages as thumbnails.
 * Supports:
 *   • Click to navigate to a page
 *   • Drag-and-drop to reorder pages (HTML5 DnD API)
 *   • Per-page context menu (rotate CW/CCW, delete)
 *   • Visual indicators for deleted pages and rotation state
 *   • Page number labels
 *
 * The panel keeps its own drag state locally and calls the provided
 * callbacks when the user commits a reorder or structural operation.
 * Thumbnails are rendered via PDF.js at a low resolution (0.3×) for performance.
 */

"use client";

import React, {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import type { PageRotateAngle } from "../../../types/editorTypes";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface PageThumbnail {
  pageNumber: number;
  dataUrl: string | null;
  deleted: boolean;
  rotationDelta: number;
  hasEdits: boolean;
}

export interface PdfPagesPanelProps {
  thumbnails: PageThumbnail[];
  currentPage: number;
  onPageClick: (pageNumber: number) => void;
  onReorder: (newOrder: number[]) => void;
  onRotatePage: (pageNumber: number, angle: PageRotateAngle) => void;
  onDeletePage: (pageNumber: number) => void;
  totalActivePages: number;
}

interface ContextMenuState {
  visible: boolean;
  x: number;
  y: number;
  pageNumber: number;
}

// ─── Thumbnail renderer (renders PDF pages at low DPI) ────────────────────────

interface ThumbnailCanvasProps {
  dataUrl: string | null;
  rotationDelta: number;
  hasEdits: boolean;
  deleted: boolean;
  isActive: boolean;
  pageNumber: number;
}

const ThumbnailCanvas: React.FC<ThumbnailCanvasProps> = ({
  dataUrl,
  rotationDelta,
  hasEdits,
  deleted,
  isActive,
  pageNumber,
}) => {
  return (
    <div
      className={`
        relative w-full aspect-[3/4] rounded-md overflow-hidden border-2 transition-all duration-150
        ${deleted ? "opacity-30 grayscale" : ""}
        ${isActive
          ? "border-red-500 shadow-[0_0_14px_rgba(255,0,60,0.5)]"
          : "border-transparent hover:border-red-900/50"
        }
        bg-zinc-900
      `}
    >
      {dataUrl ? (
        <img
          src={dataUrl}
          alt={`Page ${pageNumber} thumbnail`}
          className="w-full h-full object-contain"
          style={{ transform: `rotate(${rotationDelta}deg)`, transition: "transform 0.2s ease" }}
          draggable={false}
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center bg-zinc-900">
          <svg className="w-6 h-6 text-zinc-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" />
            <path d="M14 2v6h6" />
          </svg>
        </div>
      )}

      {/* Edit indicator dot */}
      {hasEdits && !deleted && (
        <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-red-500 shadow-[0_0_6px_rgba(255,0,60,0.8)]" />
      )}

      {/* Deleted overlay */}
      {deleted && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-200/60 dark:bg-slate-800/60 rounded-md">
          <span className="text-[9px] font-bold text-rose-600 dark:text-rose-400 uppercase tracking-widest rotate-[-30deg]">
            Deleted
          </span>
        </div>
      )}
    </div>
  );
};

// ─── Main component ───────────────────────────────────────────────────────────

export const PdfPagesPanel: React.FC<PdfPagesPanelProps> = ({
  thumbnails,
  currentPage,
  onPageClick,
  onReorder,
  onRotatePage,
  onDeletePage,
  totalActivePages,
}) => {
  const [dragFromIndex, setDragFromIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const [contextMenu, setContextMenu] = useState<ContextMenuState>({
    visible: false,
    x: 0,
    y: 0,
    pageNumber: 1,
  });
  const panelRef = useRef<HTMLDivElement>(null);

  // ── Close context menu on outside click ─────────────────────────────────
  useEffect(() => {
    const handle = (e: MouseEvent) => {
      if (contextMenu.visible) {
        setContextMenu((m) => ({ ...m, visible: false }));
      }
    };
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, [contextMenu.visible]);

  // ── Context menu ─────────────────────────────────────────────────────────
  const handleContextMenu = useCallback(
    (e: React.MouseEvent, pageNumber: number) => {
      e.preventDefault();
      e.stopPropagation();
      const panelRect = panelRef.current?.getBoundingClientRect();
      setContextMenu({
        visible: true,
        x: e.clientX - (panelRect?.left ?? 0),
        y: e.clientY - (panelRect?.top ?? 0),
        pageNumber,
      });
    },
    []
  );

  // ── Drag-and-drop (HTML5 DnD) ─────────────────────────────────────────────
  const handleDragStart = (e: React.DragEvent, index: number) => {
    setDragFromIndex(index);
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", String(index));
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    if (index !== dragOverIndex) setDragOverIndex(index);
  };

  const handleDrop = (e: React.DragEvent, dropIndex: number) => {
    e.preventDefault();
    if (dragFromIndex === null || dragFromIndex === dropIndex) {
      setDragFromIndex(null);
      setDragOverIndex(null);
      return;
    }

    // Build new order: reinsert dragged page at drop position
    const activePages = thumbnails
      .filter((t) => !t.deleted)
      .map((t) => t.pageNumber);

    const draggedPage = activePages[dragFromIndex];
    const newOrder = activePages.filter((_, i) => i !== dragFromIndex);
    newOrder.splice(dropIndex, 0, draggedPage);

    onReorder(newOrder);
    setDragFromIndex(null);
    setDragOverIndex(null);
  };

  const handleDragEnd = () => {
    setDragFromIndex(null);
    setDragOverIndex(null);
  };

  const activeThumbnails = thumbnails.filter((t) => !t.deleted);

  return (
    <div
      ref={panelRef}
      className="relative min-w-0 w-full bg-zinc-950
                 border-r border-red-900/30
                 flex flex-col overflow-hidden"
      aria-label="Page navigator"
    >
      {/* Header */}
      <div className="px-3 py-2 border-b border-red-900/30
                      text-xs font-semibold text-red-500/70 uppercase tracking-wider
                      flex-shrink-0">
        Pages ({activeThumbnails.length})
      </div>

      {/* Scrollable thumbnail list */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden py-2 px-2 space-y-2 scrollbar-thin scrollbar-thumb-slate-300 dark:scrollbar-thumb-slate-600">
        {activeThumbnails.map((thumb, index) => {
          const isDragging = dragFromIndex === index;
          const isDragTarget = dragOverIndex === index && dragFromIndex !== null && dragFromIndex !== index;

          return (
            <div
              key={thumb.pageNumber}
              draggable={!thumb.deleted}
              onDragStart={(e) => handleDragStart(e, index)}
              onDragOver={(e) => handleDragOver(e, index)}
              onDrop={(e) => handleDrop(e, index)}
              onDragEnd={handleDragEnd}
              onClick={() => !thumb.deleted && onPageClick(thumb.pageNumber)}
              onContextMenu={(e) => handleContextMenu(e, thumb.pageNumber)}
              className={`
                group cursor-pointer select-none rounded-lg p-1 transition-all duration-100
                ${isDragging ? "opacity-40 scale-95" : "opacity-100 scale-100"}
                ${isDragTarget ? "ring-2 ring-red-500 ring-offset-1 ring-offset-zinc-950" : ""}
                ${!thumb.deleted ? "hover:bg-zinc-800/60" : "cursor-not-allowed"}
              `}
              role="button"
              aria-label={`Go to page ${thumb.pageNumber}`}
              aria-current={currentPage === thumb.pageNumber ? "page" : undefined}
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  if (!thumb.deleted) onPageClick(thumb.pageNumber);
                }
              }}
            >
              <ThumbnailCanvas
                dataUrl={thumb.dataUrl}
                rotationDelta={thumb.rotationDelta}
                hasEdits={thumb.hasEdits}
                deleted={thumb.deleted}
                isActive={currentPage === thumb.pageNumber}
                pageNumber={thumb.pageNumber}
              />

              {/* Page number label */}
              <p className={`
                mt-1 text-center text-[10px] font-medium tabular-nums
                ${currentPage === thumb.pageNumber
                  ? "text-red-400"
                  : "text-zinc-500"
                }
              `}>
                {thumb.pageNumber}
              </p>
            </div>
          );
        })}
      </div>

      {/* Context menu */}
      {contextMenu.visible && (
        <div
          className="absolute z-50 bg-zinc-900 rounded-lg py-1 min-w-[160px] text-sm
                     border border-red-900/40 shadow-[0_0_20px_rgba(255,0,60,0.15)]"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          role="menu"
          aria-label="Page options"
          onMouseDown={(e) => e.stopPropagation()}
        >
          <ContextMenuItem
            label="Rotate Left (90°)"
            icon="↺"
            onClick={() => {
              onRotatePage(contextMenu.pageNumber, -90);
              setContextMenu((m) => ({ ...m, visible: false }));
            }}
          />
          <ContextMenuItem
            label="Rotate Right (90°)"
            icon="↻"
            onClick={() => {
              onRotatePage(contextMenu.pageNumber, 90);
              setContextMenu((m) => ({ ...m, visible: false }));
            }}
          />
          <div className="my-1 border-t border-slate-100 dark:border-slate-700" />
          <ContextMenuItem
            label="Delete Page"
            icon="✕"
            danger
            disabled={totalActivePages <= 1}
            onClick={() => {
              if (totalActivePages > 1) {
                onDeletePage(contextMenu.pageNumber);
              }
              setContextMenu((m) => ({ ...m, visible: false }));
            }}
          />
        </div>
      )}
    </div>
  );
};

// ─── Context menu item ────────────────────────────────────────────────────────

interface ContextMenuItemProps {
  label: string;
  icon: string;
  onClick: () => void;
  danger?: boolean;
  disabled?: boolean;
}

const ContextMenuItem: React.FC<ContextMenuItemProps> = ({
  label,
  icon,
  onClick,
  danger,
  disabled,
}) => (
  <button
    type="button"
    role="menuitem"
    disabled={disabled}
    onClick={disabled ? undefined : onClick}
    className={`
      w-full flex items-center gap-2.5 px-3 py-1.5 text-left transition-colors duration-100
      focus:outline-none focus-visible:bg-zinc-800
      ${disabled
        ? "text-zinc-700 cursor-not-allowed"
        : danger
        ? "text-red-500 hover:bg-red-950/40 hover:shadow-[inset_0_0_8px_rgba(255,0,60,0.1)]"
        : "text-zinc-300 hover:bg-zinc-800 hover:text-red-400"
      }
    `}
  >
    <span className="w-4 text-center font-medium" aria-hidden="true">{icon}</span>
    {label}
  </button>
);

export default PdfPagesPanel;
