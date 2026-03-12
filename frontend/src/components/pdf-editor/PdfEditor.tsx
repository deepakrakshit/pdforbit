/**
 * PdfEditor.tsx — Root PDF Editor Component
 * ==========================================
 * Orchestrates the complete PDF editor experience:
 *
 *   ┌────────────────────────────────────────────────────────┐
 *   │  PdfToolbar                                             │
 *   ├──────────┬──────────────────────────────────┬──────────┤
 *   │          │                                  │          │
 *   │  Pages   │    PdfCanvasLayer (scrollable)   │ Props    │
 *   │  Panel   │    (one page visible at a time)  │ Panel    │
 *   │          │                                  │          │
 *   └──────────┴──────────────────────────────────┴──────────┘
 *
 * Responsibilities:
 *   1. Load PDF via PDF.js (configured with worker URL)
 *   2. Render the current page through PdfCanvasLayer
 *   3. Generate thumbnails for all pages via PDF.js at low DPI
 *   4. Coordinate tool state, undo/redo, zoom
 *   5. Handle image/signature insertion (file picker → base64)
 *   6. On Apply: serialise operations via EditorStateManager and
 *      POST to the backend ``/api/v1/jobs`` endpoint (tool_id: "editor_apply")
 *   7. Poll job status until completion, then trigger download
 *
 * Usage:
 *   <PdfEditor fileId="file_abc123" fileName="contract.pdf" pdfUrl="/api/v1/files/file_abc123/download" />
 */

"use client";

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { getAccessToken } from "@/lib/auth";

import PdfCanvasLayer, {
  PdfCanvasLayerHandle,
} from "./PdfCanvasLayer";
import PdfPagesPanel, { PageThumbnail } from "./PdfPagesPanel";
import PdfPropertiesPanel from "./PdfPropertiesPanel";
import PdfToolbar from "./PdfToolbar";
import { EditorStateManager } from "./editorStateManager";
import type {
  DrawProperties,
  EditorTool,
  HighlightProperties,
  PageDimensions,
  PageRotateAngle,
  ShapeProperties,
  TextProperties,
} from "../../../types/editorTypes";
import {
  DEFAULT_FONT_SIZE,
  DEFAULT_HIGHLIGHT_COLOR,
  DEFAULT_SHAPE_FILL_COLOR,
  DEFAULT_SHAPE_STROKE_COLOR,
  DEFAULT_STROKE_WIDTH,
  DEFAULT_TEXT_COLOR,
} from "../../../types/editorTypes";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface PdfEditorProps {
  /** PdfORBIT file_id (e.g. "file_abc123xyz") */
  fileId: string;
  /** Original filename for the output PDF */
  fileName: string;
  /** Direct URL from which to load the PDF (pre-signed or API route) */
  pdfUrl: string;
  /** API base URL, defaults to "/api/v1" */
  apiBase?: string;
  /** Called when the apply job completes and download is ready */
  onDownloadReady?: (downloadUrl: string) => void;
  /** Called when the editor is dismissed */
  onClose?: () => void;
}

interface JobStatusResponse {
  job_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  error?: string;
  download_url?: string;
}

// ─── PDF.js worker setup ──────────────────────────────────────────────────────

function getPdfWorkerUrl(version?: string): string {
  const resolvedVersion = version || "4.10.38";
  return `https://cdn.jsdelivr.net/npm/pdfjs-dist@${resolvedVersion}/build/pdf.worker.min.mjs`;
}

// ─── Thumbnail DPI ────────────────────────────────────────────────────────────
const THUMBNAIL_SCALE = 0.25;
const MIN_ZOOM = 0.25;
const MAX_ZOOM = 4;
const ZOOM_STEP = 0.1;

// ─── Job polling interval ─────────────────────────────────────────────────────
const POLL_INTERVAL_MS = 1500;
const MAX_POLL_ATTEMPTS = 120; // 3 minutes

function parseEditorColor(color: string): { r: number; g: number; b: number } | null {
  if (!color || color === "transparent") {
    return null;
  }

  const normalized = color.trim();
  const shortHex = normalized.match(/^#([0-9a-f]{3})$/i);
  if (shortHex) {
    const [r, g, b] = shortHex[1].split("").map((value) => parseInt(value + value, 16));
    return { r, g, b };
  }

  const longHex = normalized.match(/^#([0-9a-f]{6})$/i);
  if (longHex) {
    return {
      r: parseInt(longHex[1].slice(0, 2), 16),
      g: parseInt(longHex[1].slice(2, 4), 16),
      b: parseInt(longHex[1].slice(4, 6), 16),
    };
  }

  const rgb = normalized.match(/^rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
  if (rgb) {
    return {
      r: parseInt(rgb[1], 10),
      g: parseInt(rgb[2], 10),
      b: parseInt(rgb[3], 10),
    };
  }

  return null;
}

function toHexColor(color: string | undefined, fallback: string): string {
  const rgb = color ? parseEditorColor(color) : null;
  if (!rgb) {
    return fallback;
  }

  return (
    "#" +
    [rgb.r, rgb.g, rgb.b]
      .map((value) => value.toString(16).padStart(2, "0"))
      .join("")
      .toUpperCase()
  );
}

function normalizeEditorFontName(fontFamily: string | undefined): TextProperties["fontName"] {
  const normalized = (fontFamily ?? "helv").toLowerCase().replace(/[^a-z]/g, "");
  const bold = normalized.includes("bold");
  const italic = normalized.includes("italic") || normalized.includes("oblique");

  if (normalized.startsWith("tim") || normalized.includes("times")) {
    if (bold && italic) return "timbi";
    if (bold) return "timb";
    if (italic) return "timi";
    return "timr";
  }

  if (normalized.startsWith("cou") || normalized.includes("courier")) {
    if (bold && italic) return "courbi";
    if (bold) return "courb";
    if (italic) return "couri";
    return "cour";
  }

  if (normalized.includes("symbol")) return "symb";
  if (normalized.includes("zapf")) return "zadb";
  if (bold && italic) return "helv-bold-italic";
  if (bold) return "helv-bold";
  if (italic) return "helv-italic";
  return "helv";
}

function toCanvasColor(color: string, opacity: number): string {
  const rgb = parseEditorColor(color);
  const clampedOpacity = Math.max(0, Math.min(1, opacity));
  if (!rgb || clampedOpacity <= 0) {
    return "transparent";
  }
  return `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${clampedOpacity})`;
}

function resolveDownloadUrl(downloadUrl: string, apiBase: string): string {
  if (/^https?:\/\//i.test(downloadUrl)) {
    return downloadUrl;
  }

  if (typeof window === "undefined") {
    return downloadUrl;
  }

  if (/^https?:\/\//i.test(apiBase)) {
    return new URL(downloadUrl, apiBase).toString();
  }

  return new URL(downloadUrl, window.location.origin).toString();
}

function buildAuthHeaders(extraHeaders?: HeadersInit): HeadersInit {
  const accessToken = getAccessToken();
  return {
    ...(extraHeaders ?? {}),
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
  };
}

// ─── Default tool property bags ───────────────────────────────────────────────
const defaultTextProps: TextProperties = {
  text: "",
  fontSize: DEFAULT_FONT_SIZE,
  fontName: "helv",
  color: DEFAULT_TEXT_COLOR,
  align: "left",
  bold: false,
  italic: false,
  opacity: 1,
  lineHeight: 1.2,
};

const defaultDrawProps: DrawProperties = {
  color: "#1a1a1a",
  strokeWidth: DEFAULT_STROKE_WIDTH,
  opacity: 1,
  capStyle: "round",
  joinStyle: "round",
};

const defaultShapeProps: ShapeProperties = {
  shapeType: "rect",
  fillColor: DEFAULT_SHAPE_FILL_COLOR,
  strokeColor: DEFAULT_SHAPE_STROKE_COLOR,
  strokeWidth: 1.5,
  fillOpacity: 0,
  strokeOpacity: 1,
};

const defaultHighlightProps: HighlightProperties = {
  color: DEFAULT_HIGHLIGHT_COLOR,
  opacity: 0.45,
};

// ─── Main component ───────────────────────────────────────────────────────────

const PdfEditor: React.FC<PdfEditorProps> = ({
  fileId,
  fileName,
  pdfUrl,
  apiBase = "/api/v1",
  onDownloadReady,
  onClose,
}) => {
  // ── PDF.js document ──────────────────────────────────────────────────────
  const [pdfDocument, setPdfDocument] = useState<any>(null); // PDFDocumentProxy
  const [pageCount, setPageCount] = useState(0);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isPdfLoading, setIsPdfLoading] = useState(true);

  // ── Page navigation ──────────────────────────────────────────────────────
  const [currentPage, setCurrentPage] = useState(1);

  // ── Thumbnails ───────────────────────────────────────────────────────────
  const [thumbnails, setThumbnails] = useState<PageThumbnail[]>([]);

  // ── Zoom ─────────────────────────────────────────────────────────────────
  const [zoom, setZoom] = useState(1.0);
  const zoomRef = useRef(1.0);
  const [isSpacePressed, setIsSpacePressed] = useState(false);
  const [isPanning, setIsPanning] = useState(false);

  // ── Tool state ───────────────────────────────────────────────────────────
  const [activeTool, setActiveTool] = useState<EditorTool>("select");
  const [textProps, setTextProps] = useState<TextProperties>(defaultTextProps);
  const [drawProps, setDrawProps] = useState<DrawProperties>(defaultDrawProps);
  const [shapeProps, setShapeProps] = useState<ShapeProperties>(defaultShapeProps);
  const [highlightProps, setHighlightProps] = useState<HighlightProperties>(defaultHighlightProps);
  const [selectedObjectType, setSelectedObjectType] = useState<string | null>(null);

  // ── Apply state ──────────────────────────────────────────────────────────
  const [isApplying, setIsApplying] = useState(false);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [applyProgress, setApplyProgress] = useState(0);

  // ── Undo/redo state ──────────────────────────────────────────────────────
  const [undoDepth, setUndoDepth] = useState(0);
  const [redoDepth, setRedoDepth] = useState(0);
  const [isDirty, setIsDirty] = useState(false);

  // ── Refs ─────────────────────────────────────────────────────────────────
  const canvasLayerRef = useRef<PdfCanvasLayerHandle>(null);
  const stateManagerRef = useRef<EditorStateManager | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [containerWidth, setContainerWidth] = useState(800);
  const wheelZoomRafRef = useRef<number | null>(null);
  const wheelZoomDeltaRef = useRef(0);
  const wheelPointerRef = useRef<{ clientX: number; clientY: number } | null>(null);
  const panSessionRef = useRef<{
    startX: number;
    startY: number;
    scrollLeft: number;
    scrollTop: number;
  } | null>(null);

  // ── Track active tool for image/signature mode ───────────────────────────
  const pendingImageToolRef = useRef<"image" | "signature" | null>(null);

  useEffect(() => {
    zoomRef.current = zoom;
  }, [zoom]);

  // ─── Load PDF.js ─────────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;

    const loadPdf = async () => {
      try {
        setIsPdfLoading(true);
        setLoadError(null);

        // Dynamic import (Next.js / webpack)
        const pdfjsLib = await import("pdfjs-dist" as string);
        pdfjsLib.GlobalWorkerOptions.workerSrc = getPdfWorkerUrl(pdfjsLib.version);

        const loadingTask = pdfjsLib.getDocument(pdfUrl);
        const doc = await loadingTask.promise;

        if (cancelled) {
          doc.destroy();
          return;
        }

        // Build state manager
        const sm = new EditorStateManager(fileId, fileName, doc.numPages);
        stateManagerRef.current = sm;

        setPageCount(doc.numPages);
        setPdfDocument(doc);
        setCurrentPage(1);

        // Generate thumbnails in background
        _generateThumbnails(doc, doc.numPages);
      } catch (err: any) {
        if (!cancelled) {
          console.error("[PdfEditor] Failed to load PDF:", err);
          setLoadError(err?.message ?? "Failed to load PDF.");
        }
      } finally {
        if (!cancelled) setIsPdfLoading(false);
      }
    };

    loadPdf();

    return () => {
      cancelled = true;
    };
  }, [fileId, fileName, pdfUrl]);

  // ─── Thumbnail generation ─────────────────────────────────────────────────
  const _generateThumbnails = useCallback(
    async (doc: any, numPages: number) => {
      const initial: PageThumbnail[] = Array.from({ length: numPages }, (_, i) => ({
        pageNumber: i + 1,
        dataUrl: null,
        deleted: false,
        rotationDelta: 0,
        hasEdits: false,
      }));
      setThumbnails(initial);

      for (let p = 1; p <= numPages; p++) {
        try {
          const page = await doc.getPage(p);
          const viewport = page.getViewport({ scale: THUMBNAIL_SCALE });
          const canvas = document.createElement("canvas");
          canvas.width = Math.round(viewport.width);
          canvas.height = Math.round(viewport.height);
          const ctx = canvas.getContext("2d");
          if (!ctx) continue;
          await page.render({ canvasContext: ctx, viewport }).promise;
          const dataUrl = canvas.toDataURL("image/jpeg", 0.7);

          setThumbnails((prev) =>
            prev.map((t) =>
              t.pageNumber === p ? { ...t, dataUrl } : t
            )
          );
        } catch (err) {
          console.warn(`[PdfEditor] Thumbnail generation failed for page ${p}:`, err);
        }
      }
    },
    []
  );

  // ─── Container width observer ─────────────────────────────────────────────
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect?.width;
      if (w && w !== containerWidth) setContainerWidth(Math.round(w));
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, [containerWidth]);

  // ─── Undo/redo ────────────────────────────────────────────────────────────
  const _syncHistoryState = useCallback(() => {
    const sm = stateManagerRef.current;
    if (!sm) return;
    setUndoDepth(sm.undoDepth);
    setRedoDepth(sm.redoDepth);
    setIsDirty(sm.isDirty());
    setThumbnails((prev) =>
      prev.map((thumbnail) => ({
        ...thumbnail,
        hasEdits: sm.hasPageChanges(thumbnail.pageNumber) || sm.getPageRotation(thumbnail.pageNumber) !== 0,
        deleted: sm.isPageDeleted(thumbnail.pageNumber),
      }))
    );
  }, []);

  const clampZoom = useCallback((value: number) => {
    return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Number(value.toFixed(2))));
  }, []);

  const applyZoom = useCallback(
    (nextZoom: number, anchor?: { clientX: number; clientY: number }) => {
      const viewport = viewportRef.current;
      const previousZoom = zoomRef.current;
      const boundedZoom = clampZoom(nextZoom);
      if (!viewport || Math.abs(previousZoom - boundedZoom) < 0.001) {
        setZoom(boundedZoom);
        return;
      }

      const rect = viewport.getBoundingClientRect();
      const anchorClientX = anchor?.clientX ?? rect.left + rect.width / 2;
      const anchorClientY = anchor?.clientY ?? rect.top + rect.height / 2;
      const anchorOffsetX = anchorClientX - rect.left;
      const anchorOffsetY = anchorClientY - rect.top;
      const contentX = viewport.scrollLeft + anchorOffsetX;
      const contentY = viewport.scrollTop + anchorOffsetY;
      const ratio = boundedZoom / previousZoom;

      setZoom(boundedZoom);

      requestAnimationFrame(() => {
        viewport.scrollLeft = Math.max(0, contentX * ratio - anchorOffsetX);
        viewport.scrollTop = Math.max(0, contentY * ratio - anchorOffsetY);
      });
    },
    [clampZoom]
  );

  const handleUndo = useCallback(() => {
    const sm = stateManagerRef.current;
    if (!sm) return;
    sm.undo();
    _syncHistoryState();
    canvasLayerRef.current?.getFabricCanvas()?.loadFromJSON(
      {
        version: "5.3.0",
        objects: sm.getCanvasObjects(currentPage),
      },
      () => canvasLayerRef.current?.getFabricCanvas()?.requestRenderAll()
    );
  }, [currentPage, _syncHistoryState]);

  const handleRedo = useCallback(() => {
    const sm = stateManagerRef.current;
    if (!sm) return;
    sm.redo();
    _syncHistoryState();
    canvasLayerRef.current?.getFabricCanvas()?.loadFromJSON(
      {
        version: "5.3.0",
        objects: sm.getCanvasObjects(currentPage),
      },
      () => canvasLayerRef.current?.getFabricCanvas()?.requestRenderAll()
    );
  }, [currentPage, _syncHistoryState]);

  // ─── Page navigation ──────────────────────────────────────────────────────
  const handlePageClick = useCallback(
    (pageNumber: number) => {
      if (pageNumber === currentPage) return;
      // Save current page state before switching
      canvasLayerRef.current?.saveCurrentPage();
      setCurrentPage(pageNumber);
    },
    [currentPage]
  );

  // ─── Page dimensions callback ─────────────────────────────────────────────
  const handleDimensionsReady = useCallback((_dims: PageDimensions) => {
    // Dimensions are already set on the state manager by PdfCanvasLayer
    // nothing more needed here
  }, []);

  const commitObjectMutation = useCallback((description: string, mutate: (obj: any, fc: any) => void) => {
    const sm = stateManagerRef.current;
    const fc = canvasLayerRef.current?.getFabricCanvas();
    const obj = fc?.getActiveObject();
    if (!sm || !fc || !obj) return false;

    sm.saveSnapshot(description);
    mutate(obj, fc);
    obj.setCoords?.();
    fc.requestRenderAll();
    canvasLayerRef.current?.saveCurrentPage();
    _syncHistoryState();
    return true;
  }, [_syncHistoryState]);

  // ─── Object selection ─────────────────────────────────────────────────────
  const handleObjectSelected = useCallback((obj: any | null) => {
    if (!obj) {
      setSelectedObjectType(null);
      return;
    }
    const orbType = (obj as any).orbType ?? obj.type;
    setSelectedObjectType(orbType ?? null);

    if (orbType === "text" || orbType === "textbox" || orbType === "i-text" || orbType === "existing-text") {
      setTextProps((prev) => ({
        ...prev,
        text: obj.text ?? prev.text,
        fontSize: obj.fontSize ?? prev.fontSize,
        fontName: normalizeEditorFontName(obj.fontFamily ?? obj.orbSourceFontName ?? prev.fontName),
        color: toHexColor(obj.fill ?? obj.orbSourceColor, prev.color),
        align: obj.textAlign ?? obj.orbSourceAlign ?? prev.align,
        bold: obj.fontWeight === "bold",
        italic: obj.fontStyle === "italic",
        opacity: obj.opacity ?? obj.orbSourceOpacity ?? prev.opacity,
        lineHeight: obj.lineHeight ?? obj.orbSourceLineHeight ?? prev.lineHeight,
      }));
    } else if (orbType === "draw" || orbType === "path") {
      setDrawProps((prev) => ({
        ...prev,
        color: toHexColor(obj.stroke, prev.color),
        strokeWidth: obj.strokeWidth ?? prev.strokeWidth,
        opacity: obj.opacity ?? prev.opacity,
        capStyle: obj.strokeLineCap ?? prev.capStyle,
        joinStyle: obj.strokeLineJoin ?? prev.joinStyle,
      }));
    } else if (orbType === "highlight") {
      setHighlightProps((prev) => ({
        ...prev,
        color: toHexColor(obj.fill, prev.color),
        opacity: obj.opacity ?? prev.opacity,
      }));
    } else if (orbType === "rect" || orbType === "circle" || orbType === "line") {
      setShapeProps((prev) => ({
        ...prev,
        shapeType: orbType === "circle" ? "circle" : orbType === "line" ? "line" : "rect",
        fillColor: toHexColor(obj.fill, prev.fillColor),
        strokeColor: toHexColor(obj.stroke, prev.strokeColor),
        strokeWidth: obj.strokeWidth ?? prev.strokeWidth,
        fillOpacity: (obj as any).orbFillOpacity ?? prev.fillOpacity,
        strokeOpacity: (obj as any).orbStrokeOpacity ?? prev.strokeOpacity,
      }));
    }
  }, []);

  // ─── Tool change ──────────────────────────────────────────────────────────
  const handleToolChange = useCallback((tool: EditorTool) => {
    setActiveTool(tool);
    canvasLayerRef.current?.deselectAll();
    setSelectedObjectType(null);

    // For image/signature tools, trigger the hidden file input immediately
    if (tool === "image" || tool === "signature") {
      pendingImageToolRef.current = tool;
      fileInputRef.current?.click();
    }
  }, []);

  // ─── Image file input handler ─────────────────────────────────────────────
  const handleFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) {
        setActiveTool("select");
        return;
      }

      const reader = new FileReader();
      reader.onload = (ev) => {
        const dataUrl = ev.target?.result as string;
        if (!dataUrl) return;

        // Access the insertImage method exposed via the container ref trick
        const container = (canvasLayerRef.current as any)?._fabricContainerRef?.insertImage;
        // Direct approach: find canvas by rendered page
        const isSignature = pendingImageToolRef.current === "signature";

        // We trigger insertion by dispatching a custom event the canvas layer listens to
        const event = new CustomEvent("editor:insert-image", {
          detail: { dataUrl, isSignature },
        });
        document.dispatchEvent(event);

        // Reset tool to select after insertion
        setActiveTool("select");
        pendingImageToolRef.current = null;

        // Mark as dirty
        setIsDirty(true);
        _syncHistoryState();
      };
      reader.readAsDataURL(file);

      // Reset input so the same file can be picked again
      e.target.value = "";
    },
    [_syncHistoryState]
  );

  // ─── Structural page operations ───────────────────────────────────────────
  const handleRotatePage = useCallback(
    (angle: PageRotateAngle, pageNumber = currentPage) => {
      const sm = stateManagerRef.current;
      if (!sm) return;
      if (pageNumber === currentPage) {
        canvasLayerRef.current?.saveCurrentPage();
      }
      sm.rotatePage(pageNumber, angle);
      setThumbnails((prev) =>
        prev.map((t) =>
          t.pageNumber === pageNumber
            ? { ...t, rotationDelta: (t.rotationDelta + angle + 360) % 360 }
            : t
        )
      );
      _syncHistoryState();
    },
    [currentPage, _syncHistoryState]
  );

  const handleDeletePage = useCallback((pageNumber = currentPage) => {
    const sm = stateManagerRef.current;
    if (!sm) return;
    try {
      sm.deletePage(pageNumber);
      setThumbnails((prev) =>
        prev.map((t) =>
          t.pageNumber === pageNumber ? { ...t, deleted: true } : t
        )
      );
      if (pageNumber === currentPage) {
        const order = sm.getPageOrder();
        if (order.length > 0) {
          const nextPage = order.includes(currentPage) ? currentPage : order[0];
          setCurrentPage(nextPage);
        }
      }
      _syncHistoryState();
    } catch (err: any) {
      console.warn("[PdfEditor] Delete page failed:", err?.message);
    }
  }, [currentPage, _syncHistoryState]);

  const handleReorder = useCallback(
    (newOrder: number[]) => {
      const sm = stateManagerRef.current;
      if (!sm) return;
      sm.reorderPages(newOrder);
      // Reorder thumbnails to match
      setThumbnails((prev) => {
        const map = new Map(prev.map((t) => [t.pageNumber, t]));
        return newOrder.map((p) => map.get(p)!).filter(Boolean);
      });
      _syncHistoryState();
    },
    [_syncHistoryState]
  );

  // ─── Zoom ─────────────────────────────────────────────────────────────────
  const handleZoomIn = useCallback(() => {
    applyZoom(zoomRef.current + ZOOM_STEP);
  }, [applyZoom]);

  const handleZoomOut = useCallback(() => {
    applyZoom(zoomRef.current - ZOOM_STEP);
  }, [applyZoom]);

  const handleZoomReset = useCallback(() => {
    applyZoom(1.0);
  }, [applyZoom]);

  const handleZoomChange = useCallback(
    (nextZoom: number) => {
      applyZoom(nextZoom);
    },
    [applyZoom]
  );

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const tag = (event.target as HTMLElement | null)?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") {
        return;
      }
      if (event.code === "Space") {
        event.preventDefault();
        setIsSpacePressed(true);
      }
    };

    const handleKeyUp = (event: KeyboardEvent) => {
      if (event.code === "Space") {
        setIsSpacePressed(false);
        setIsPanning(false);
        panSessionRef.current = null;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, []);

  const handleViewportWheel = useCallback(
    (event: React.WheelEvent<HTMLDivElement>) => {
      if (!event.ctrlKey) {
        return;
      }

      event.preventDefault();
      wheelZoomDeltaRef.current += event.deltaY;
      wheelPointerRef.current = { clientX: event.clientX, clientY: event.clientY };

      if (wheelZoomRafRef.current !== null) {
        return;
      }

      wheelZoomRafRef.current = window.requestAnimationFrame(() => {
        const delta = wheelZoomDeltaRef.current;
        const pointer = wheelPointerRef.current;
        wheelZoomDeltaRef.current = 0;
        wheelPointerRef.current = null;
        wheelZoomRafRef.current = null;

        const multiplier = Math.exp(-delta * 0.0015);
        applyZoom(zoomRef.current * multiplier, pointer ?? undefined);
      });
    },
    [applyZoom]
  );

  const endPanning = useCallback(() => {
    setIsPanning(false);
    panSessionRef.current = null;
  }, []);

  const handleViewportMouseDown = useCallback(
    (event: React.MouseEvent<HTMLDivElement>) => {
      const viewport = viewportRef.current;
      if (!viewport) return;

      const shouldPan = isSpacePressed || activeTool === "pan";
      if (!shouldPan) {
        return;
      }

      event.preventDefault();
      panSessionRef.current = {
        startX: event.clientX,
        startY: event.clientY,
        scrollLeft: viewport.scrollLeft,
        scrollTop: viewport.scrollTop,
      };
      setIsPanning(true);
    },
    [activeTool, isSpacePressed]
  );

  useEffect(() => {
    const handlePointerMove = (event: MouseEvent) => {
      const session = panSessionRef.current;
      const viewport = viewportRef.current;
      if (!session || !viewport) {
        return;
      }

      const deltaX = event.clientX - session.startX;
      const deltaY = event.clientY - session.startY;
      viewport.scrollLeft = session.scrollLeft - deltaX;
      viewport.scrollTop = session.scrollTop - deltaY;
    };

    const handlePointerUp = () => {
      endPanning();
    };

    window.addEventListener("mousemove", handlePointerMove);
    window.addEventListener("mouseup", handlePointerUp);
    return () => {
      window.removeEventListener("mousemove", handlePointerMove);
      window.removeEventListener("mouseup", handlePointerUp);
    };
  }, [endPanning]);

  // ─── Properties panel change handlers ────────────────────────────────────
  const handleTextPropsChange = useCallback((p: Partial<TextProperties>) => {
    setTextProps((prev: TextProperties) => ({ ...prev, ...p }));
    commitObjectMutation("Edit text properties", (obj) => {
      if (p.color !== undefined) (obj as any).set({ fill: p.color });
      if (p.fontSize !== undefined) (obj as any).set({ fontSize: p.fontSize });
      if (p.fontName !== undefined) (obj as any).set({ fontFamily: p.fontName });
      if (p.align !== undefined) (obj as any).set({ textAlign: p.align });
      if (p.bold !== undefined) (obj as any).set({ fontWeight: p.bold ? "bold" : "normal" });
      if (p.italic !== undefined) (obj as any).set({ fontStyle: p.italic ? "italic" : "normal" });
      if (p.opacity !== undefined) (obj as any).set({ opacity: p.opacity });
      if (p.lineHeight !== undefined) (obj as any).set({ lineHeight: p.lineHeight });
    });
  }, [commitObjectMutation]);

  const handleDrawPropsChange = useCallback((p: Partial<DrawProperties>) => {
    setDrawProps((prev: DrawProperties) => ({ ...prev, ...p }));
    const fc = canvasLayerRef.current?.getFabricCanvas();
    // Apply to free drawing brush (if active)
    if (fc?.isDrawingMode && fc.freeDrawingBrush) {
      if (p.color !== undefined) fc.freeDrawingBrush.color = p.color;
      if (p.strokeWidth !== undefined) fc.freeDrawingBrush.width = p.strokeWidth;
    }
    commitObjectMutation("Edit draw properties", (obj) => {
      if (p.color !== undefined) obj.set({ stroke: p.color });
      if (p.strokeWidth !== undefined) obj.set({ strokeWidth: p.strokeWidth });
      if (p.opacity !== undefined) obj.set({ opacity: p.opacity });
      if (p.capStyle !== undefined) obj.set({ strokeLineCap: p.capStyle });
      if (p.joinStyle !== undefined) obj.set({ strokeLineJoin: p.joinStyle });
    });
  }, [commitObjectMutation]);

  const handleShapePropsChange = useCallback((p: Partial<ShapeProperties>) => {
    setShapeProps((prev: ShapeProperties) => ({ ...prev, ...p }));
    commitObjectMutation("Edit shape properties", (obj) => {
      const orbType = (obj as any).orbType ?? obj.type;
      const nextFillColor = p.fillColor ?? toHexColor((obj as any).fill, shapeProps.fillColor);
      const nextFillOpacity = p.fillOpacity ?? (obj as any).orbFillOpacity ?? shapeProps.fillOpacity;
      const nextStrokeColor = p.strokeColor ?? toHexColor((obj as any).stroke, shapeProps.strokeColor);
      const nextStrokeOpacity = p.strokeOpacity ?? (obj as any).orbStrokeOpacity ?? shapeProps.strokeOpacity;

      const nextProps: Record<string, unknown> = {};
      if (orbType !== "line") {
        nextProps.fill = toCanvasColor(nextFillColor, nextFillOpacity);
      }
      nextProps.stroke = toCanvasColor(nextStrokeColor, nextStrokeOpacity);
      if (p.strokeWidth !== undefined) {
        nextProps.strokeWidth = p.strokeWidth;
      }

      obj.set(nextProps);
      (obj as any).orbFillOpacity = nextFillOpacity;
      (obj as any).orbStrokeOpacity = nextStrokeOpacity;
    });
  }, [commitObjectMutation, shapeProps.fillColor, shapeProps.fillOpacity, shapeProps.strokeColor, shapeProps.strokeOpacity]);

  const handleHighlightPropsChange = useCallback(
    (p: Partial<HighlightProperties>) => {
      setHighlightProps((prev: HighlightProperties) => ({ ...prev, ...p }));
      commitObjectMutation("Edit highlight properties", (obj) => {
        if (p.color !== undefined) obj.set({ fill: p.color });
        if (p.opacity !== undefined) obj.set({ opacity: p.opacity });
      });
    },
    [commitObjectMutation]
  );

  // ─── Delete selected object ───────────────────────────────────────────────
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Delete" || e.key === "Backspace") {
        const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
        if (tag === "input" || tag === "textarea") return;
        canvasLayerRef.current?.deleteSelectedObjects();
        _syncHistoryState();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [_syncHistoryState]);

  // ─── Apply editor changes ─────────────────────────────────────────────────
  const handleApply = useCallback(async () => {
    const sm = stateManagerRef.current;
    if (!sm) return;

    // Save current page before exporting
    canvasLayerRef.current?.saveCurrentPage();

    const operations = sm.exportOperations();
    if (operations.length === 0) {
      setApplyError("No edits to apply.");
      return;
    }
    if (operations.length > 2000) {
      setApplyError(
        `This document has ${operations.length} editor operations, which exceeds the 2,000 limit. ` +
        "Try splitting edits across multiple saves."
      );
      return;
    }

    const outputFilename = fileName.replace(/\.pdf$/i, "") + "_edited.pdf";
    const requestPayload = {
      file_id: fileId,
      output_filename: outputFilename,
      operations,
      canvas_width: containerWidth,
    };

    setIsApplying(true);
    setApplyError(null);
    setApplyProgress(0);

    try {
      // 1. Create job
      const createRes = await fetch(`${apiBase}/jobs`, {
        method: "POST",
        headers: buildAuthHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ tool_id: "editor_apply", payload: requestPayload }),
        credentials: "include",
      });

      if (!createRes.ok) {
        const errBody = await createRes.json().catch(() => ({}));
        throw new Error(errBody?.detail ?? `Job creation failed: ${createRes.status}`);
      }

      const { job_id } = await createRes.json() as { job_id: string };

      // 2. Poll for completion
      await _pollJobStatus(job_id);
    } catch (err: any) {
      console.error("[PdfEditor] Apply failed:", err);
      setApplyError(err?.message ?? "Failed to apply editor changes.");
    } finally {
      setIsApplying(false);
    }
  }, [fileId, fileName, apiBase, containerWidth]);

  const _pollJobStatus = useCallback(
    async (jobId: string): Promise<void> => {
      let attempts = 0;

      return new Promise((resolve, reject) => {
        const poll = async () => {
          attempts++;
          if (attempts > MAX_POLL_ATTEMPTS) {
            reject(new Error("The editing job timed out. Please try again."));
            return;
          }

          try {
            const res = await fetch(`${apiBase}/jobs/${jobId}`, {
              headers: buildAuthHeaders(),
              credentials: "include",
            });
            if (!res.ok) throw new Error(`Status poll failed: ${res.status}`);

            const status = await res.json() as JobStatusResponse;
            setApplyProgress(status.progress ?? 0);

            if (status.status === "completed" && status.download_url) {
              const downloadUrl = resolveDownloadUrl(status.download_url, apiBase);
              if (onDownloadReady) {
                onDownloadReady(downloadUrl);
              } else {
                // Auto-trigger download
                const a = document.createElement("a");
                a.href = downloadUrl;
                a.download = fileName.replace(/\.pdf$/i, "") + "_edited.pdf";
                a.rel = "noopener";
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
              }
              resolve();
            } else if (status.status === "failed") {
              reject(new Error(status.error ?? "The editing job failed."));
            } else {
              pollTimerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
            }
          } catch (err) {
            reject(err);
          }
        };

        poll();
      });
    },
    [apiBase, fileName, onDownloadReady]
  );

  // Cleanup poll timer on unmount
  useEffect(() => {
    return () => {
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
      if (wheelZoomRafRef.current !== null) {
        window.cancelAnimationFrame(wheelZoomRafRef.current);
      }
    };
  }, []);

  // ─── Computed state ───────────────────────────────────────────────────────
  const activePageCount = useMemo(() => {
    const sm = stateManagerRef.current;
    return sm ? sm.getPageOrder().length : pageCount;
  }, [pageCount, isDirty]);

  const canDeletePage = activePageCount > 1;
  const canvasViewportWidth = Math.max(containerWidth - 48, 320);
  const currentPageRotation = stateManagerRef.current?.getPageRotation(currentPage) ?? 0;

  // ─── Render ───────────────────────────────────────────────────────────────

  if (loadError) {
    return (
      <div className="flex items-center justify-center h-full bg-black">
        <div className="text-center p-8 max-w-md">
          <div className="w-12 h-12 rounded-full bg-red-950/40 border border-red-900/50 flex items-center justify-center mx-auto mb-4 shadow-[0_0_20px_rgba(255,0,60,0.3)]">
            <svg viewBox="0 0 24 24" className="w-6 h-6 text-red-500" fill="none" stroke="currentColor" strokeWidth={2}>
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
          </div>
          <h2 className="text-base font-semibold text-zinc-200 mb-2">
            Failed to load PDF
          </h2>
          <p className="text-sm text-zinc-500 mb-4">{loadError}</p>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm font-medium bg-zinc-900 border border-zinc-700 hover:border-red-500/50 text-zinc-300 hover:text-red-400 transition-colors"
            >
              Close
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      className="flex flex-col w-full bg-black"
      style={{ height: "calc(100dvh - 64px)", marginTop: "64px" }}
    >
      {/* Hidden file input for image/signature insertion */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        className="hidden"
        onChange={handleFileInputChange}
        aria-hidden="true"
      />

      {/* ── Toolbar ─────────────────────────────────────────────────────── */}
      <PdfToolbar
        activeTool={activeTool}
        onToolChange={handleToolChange}
        onRotatePage={handleRotatePage}
        onDeletePage={handleDeletePage}
        onUndo={handleUndo}
        onRedo={handleRedo}
        onApply={handleApply}
        onZoomIn={handleZoomIn}
        onZoomOut={handleZoomOut}
        onZoomReset={handleZoomReset}
        onZoomChange={handleZoomChange}
        undoDisabled={undoDepth === 0}
        redoDisabled={redoDepth === 0}
        applyDisabled={!isDirty || isPdfLoading}
        isApplying={isApplying}
        currentZoom={zoom}
        currentPage={currentPage}
        totalPages={pageCount}
        canDeletePage={canDeletePage}
        onClose={onClose}
      />

      {/* ── Apply progress bar ───────────────────────────────────────────── */}
      {isApplying && (
        <div className="flex-shrink-0 h-0.5 bg-zinc-900">
          <div
            className="h-full bg-red-500 transition-all duration-300 shadow-[0_0_8px_rgba(255,0,60,0.8)]"
            style={{ width: `${applyProgress}%` }}
          />
        </div>
      )}

      {/* ── Apply error banner ───────────────────────────────────────────── */}
      {applyError && (
        <div className="flex-shrink-0 bg-red-950/30 border-b border-red-900/50 px-4 py-2 flex items-center justify-between shadow-[0_0_12px_rgba(255,0,60,0.15)]">
          <p className="text-xs text-red-400 font-medium">{applyError}</p>
          <button
            type="button"
            onClick={() => setApplyError(null)}
            className="ml-4 text-red-500 hover:text-red-300 text-xs font-medium transition-colors"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* ── Main editor area ─────────────────────────────────────────────── */}
      <div className="grid flex-1 min-h-0 overflow-hidden lg:[grid-template-columns:260px_minmax(0,1fr)_300px]">
        {/* Pages panel */}
        <PdfPagesPanel
          thumbnails={thumbnails}
          currentPage={currentPage}
          onPageClick={handlePageClick}
          onReorder={handleReorder}
          onRotatePage={(pageNumber, angle) => handleRotatePage(angle, pageNumber)}
          onDeletePage={(pageNumber) => handleDeletePage(pageNumber)}
          totalActivePages={activePageCount}
        />

        {/* Canvas area */}
        <main className="relative min-w-0 min-h-0 overflow-hidden bg-zinc-950" aria-label="PDF editor canvas">
          <div
            ref={viewportRef}
            className="absolute inset-0 overflow-auto"
            onWheel={handleViewportWheel}
            onMouseDown={handleViewportMouseDown}
            style={{
              cursor: isPanning ? "grabbing" : isSpacePressed || activeTool === "pan" ? "grab" : "default",
            }}
          >
          {isPdfLoading ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="flex flex-col items-center gap-3">
                <svg
                  className="animate-spin w-10 h-10 text-red-500"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={1.5}
                  style={{ filter: "drop-shadow(0 0 8px rgba(255,0,60,0.7))" }}
                >
                  <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                </svg>
                <span className="text-sm text-zinc-500">Loading PDF…</span>
              </div>
            </div>
          ) : (
            <div ref={containerRef} className="flex min-h-full min-w-full items-start justify-center px-8 py-8">
              <PdfCanvasLayer
                ref={canvasLayerRef}
                pdfDocument={pdfDocument}
                pageNumber={currentPage}
                pageRotation={currentPageRotation}
                activeTool={activeTool}
                zoom={zoom}
                stateManager={stateManagerRef.current}
                onDimensionsReady={handleDimensionsReady}
                onObjectSelected={handleObjectSelected}
                textProps={textProps}
                drawProps={drawProps}
                shapeProps={shapeProps}
                highlightProps={highlightProps}
                containerWidth={canvasViewportWidth}
                onCanvasStateChange={_syncHistoryState}
              />
            </div>
          )}
          </div>
        </main>

        {/* Properties panel */}
        <PdfPropertiesPanel
          activeTool={activeTool}
          selectedObjectType={selectedObjectType}
          textProps={textProps}
          drawProps={drawProps}
          shapeProps={shapeProps}
          highlightProps={highlightProps}
          onTextPropsChange={handleTextPropsChange}
          onDrawPropsChange={handleDrawPropsChange}
          onShapePropsChange={handleShapePropsChange}
          onHighlightPropsChange={handleHighlightPropsChange}
        />
      </div>

      {/* ── Status bar ───────────────────────────────────────────────────── */}
      <div
        className="flex-shrink-0 h-6 bg-zinc-950 border-t border-red-900/20
                   flex items-center gap-4 px-4 text-[10px] font-medium text-zinc-600
                   select-none"
        role="status"
        aria-live="polite"
      >
        <span className="text-zinc-500">{fileName}</span>
        <span className="opacity-30">·</span>
        <span>{pageCount} page{pageCount !== 1 ? "s" : ""}</span>
        {isDirty && (
          <>
            <span className="opacity-30">·</span>
            <span className="text-amber-500">Unsaved changes</span>
          </>
        )}
        {isApplying && (
          <>
            <span className="opacity-30">·</span>
            <span className="text-red-400" style={{ textShadow: "0 0 8px rgba(255,0,60,0.6)" }}>Applying… {applyProgress}%</span>
          </>
        )}
        <div className="flex-1" />
        <span>Zoom: {Math.round(zoom * 100)}%</span>
      </div>
    </div>
  );
};

export default PdfEditor;
