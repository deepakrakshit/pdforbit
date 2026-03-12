/**
 * PdfCanvasLayer.tsx — PDF.js Render + Fabric.js Editing Overlay
 * ==============================================================
 * This is the core canvas component of the editor. It handles:
 *
 *   1. PDF page rendering via PDF.js into a background <canvas>
 *   2. A Fabric.js canvas layered above for interactive editing
 *   3. Tool mode switching (select, text, draw, highlight, shapes, image, signature)
 *   4. Serialization of canvas objects back to the EditorStateManager
 *   5. Zoom (scale transform on the container)
 *
 * Rendering model:
 *   ┌──────────────────────────────────────┐
 *   │  div.canvas-host  (relative, sized)   │
 *   │  ┌──────────────────────────────────┐ │
 *   │  │  <canvas id="pdf-bg">            │ │  ← PDF.js renders here (background)
 *   │  │  <canvas id="fabric-upper">      │ │  ← Fabric.js: drawing / upper canvas
 *   │  │  <canvas id="fabric-lower">      │ │  ← Fabric.js: rendered objects
 *   │  └──────────────────────────────────┘ │
 *   └──────────────────────────────────────┘
 *
 * Fabric.js is loaded as a peer dependency (import * as fabric from "fabric").
 * PDF.js must be configured with a workerSrc before use.
 *
 * Performance notes:
 *   - PDF.js renders at 1.5× devicePixelRatio for crisp text
 *   - Each page's Fabric.js state is serialized to the manager on page change
 *   - Heavy operations (e.g., image loading) use Promises to avoid blocking
 */

"use client";

import React, {
  CSSProperties,
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";

import { fabric } from "fabric";

import type {
  DrawProperties,
  EditorTool,
  FontName,
  HighlightProperties,
  PageDimensions,
  ShapeProperties,
  TextAlign,
  TextProperties,
} from "../../../types/editorTypes";

import { EditorStateManager } from "./editorStateManager";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface PdfCanvasLayerProps {
  /** PDF.js PDFDocumentProxy (already loaded) */
  pdfDocument: PDFDocumentProxy | null;
  /** 1-indexed page number to render */
  pageNumber: number;
  /** Current structural page rotation in degrees */
  pageRotation: number;
  /** Current editor tool */
  activeTool: EditorTool;
  /** Zoom level (1.0 = 100%) */
  zoom: number;
  /** State manager reference */
  stateManager: EditorStateManager | null;
  /** Called when page dimensions are resolved from PDF.js */
  onDimensionsReady: (dims: PageDimensions) => void;
  /** Called when an object is selected (for properties panel) */
  onObjectSelected: (obj: fabric.Object | null) => void;
  /** Tool-specific property bags */
  textProps: TextProperties;
  drawProps: DrawProperties;
  shapeProps: ShapeProperties;
  highlightProps: HighlightProperties;
  /** Width of the container (CSS pixels) */
  containerWidth: number;
  /** Notify parent when serialized canvas state changes */
  onCanvasStateChange?: () => void;
}

export interface PdfCanvasLayerHandle {
  /** Serializes the current Fabric canvas and saves it to the state manager */
  saveCurrentPage(): void;
  /** Deletes the selected Fabric object(s) */
  deleteSelectedObjects(): void;
  /** Deselects all objects */
  deselectAll(): void;
  /** Returns the Fabric canvas instance */
  getFabricCanvas(): fabric.Canvas | null;
}

// PDF.js types (loaded via next.config.js / CDN alias)
declare global {
  interface Window {
    pdfjsLib: {
      getDocument(src: string | { data: Uint8Array }): { promise: Promise<PDFDocumentProxy> };
      GlobalWorkerOptions: { workerSrc: string };
    };
  }
}

interface PDFDocumentProxy {
  numPages: number;
  getPage(pageNumber: number): Promise<PDFPageProxy>;
  destroy(): void;
}

interface PDFPageProxy {
  getViewport(params: { scale: number; rotation?: number }): PDFViewport;
  render(params: { canvasContext: CanvasRenderingContext2D; viewport: PDFViewport }): { promise: Promise<void> };
  getTextContent(): Promise<PDFTextContent>;
}

interface PDFViewport {
  width: number;
  height: number;
  scale: number;
  transform: [number, number, number, number, number, number];
}

interface PDFTextContent {
  items: PDFTextItem[];
  styles: Record<string, PDFTextStyle>;
}

interface PDFTextItem {
  str: string;
  dir?: string;
  width: number;
  height: number;
  transform: [number, number, number, number, number, number];
  fontName: string;
  hasEOL?: boolean;
}

interface PDFTextStyle {
  fontFamily?: string;
  ascent?: number;
  descent?: number;
  vertical?: boolean;
}

interface ExtractedTextSpan {
  id: string;
  text: string;
  left: number;
  top: number;
  width: number;
  height: number;
  fontSize: number;
  fontName: FontName;
  color: string;
  opacity: number;
  align: TextAlign;
  rotation: number;
  lineHeight: number;
}

interface RawExtractedTextSpan extends ExtractedTextSpan {
  endX: number;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const PDF_RENDER_SCALE_BASE = 1.5; // base scale for PDF.js rendering
const HIGHLIGHT_RECT_BORDER = 0;   // no border on highlights
const MAX_AUTO_FIT_SCALE = 1.2;

function parseCanvasColor(color: string): { r: number; g: number; b: number } | null {
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

function toCanvasColor(color: string, opacity: number): string {
  const rgb = parseCanvasColor(color);
  const clampedOpacity = Math.max(0, Math.min(1, opacity));
  if (!rgb || clampedOpacity <= 0) {
    return "transparent";
  }
  return `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${clampedOpacity})`;
}

function multiplyTransform(
  left: [number, number, number, number, number, number],
  right: [number, number, number, number, number, number],
): [number, number, number, number, number, number] {
  return [
    left[0] * right[0] + left[2] * right[1],
    left[1] * right[0] + left[3] * right[1],
    left[0] * right[2] + left[2] * right[3],
    left[1] * right[2] + left[3] * right[3],
    left[0] * right[4] + left[2] * right[5] + left[4],
    left[1] * right[4] + left[3] * right[5] + left[5],
  ];
}

function normalizePdfFontName(fontName: string, fontFamily?: string): FontName {
  const value = `${fontFamily ?? ""} ${fontName}`.toLowerCase();
  const normalized = value.replace(/[^a-z]/g, "");
  const bold = normalized.includes("bold");
  const italic = normalized.includes("italic") || normalized.includes("oblique");

  if (normalized.includes("cour")) {
    if (bold && italic) return "courbi";
    if (bold) return "courb";
    if (italic) return "couri";
    return "cour";
  }
  if (normalized.includes("tim") || normalized.includes("times")) {
    if (bold && italic) return "timbi";
    if (bold) return "timb";
    if (italic) return "timi";
    return "timr";
  }
  if (normalized.includes("symbol")) return "symb";
  if (normalized.includes("zapf")) return "zadb";
  if (bold && italic) return "helv-bold-italic";
  if (bold) return "helv-bold";
  if (italic) return "helv-italic";
  return "helv";
}

function extractTextSpansFromContent({
  content,
  fitScale,
  pageNumber,
}: {
  content: PDFTextContent;
  fitScale: number;
  pageNumber: number;
}): ExtractedTextSpan[] {
  const textViewportTransform: [number, number, number, number, number, number] = [fitScale, 0, 0, -fitScale, 0, 0];
  const rawSpans = content.items
    .map((item, index) => {
      const style = content.styles[item.fontName] ?? {};
      const combined = multiplyTransform(textViewportTransform, item.transform);
      const fontHeight = Math.max(Math.hypot(combined[2], combined[3]), item.height || 0);
      const ascent = style.ascent ?? 0.8;
      const left = combined[4];
      const top = combined[5] - fontHeight * ascent;
      const width = Math.max(item.width * fitScale, fontHeight * 0.35, 4);
      const height = Math.max(fontHeight, 8);
      const text = item.str ?? "";
      const trimmed = text.replace(/\s+/g, " ").trim();
      if (!trimmed || width < 2 || height < 2) {
        return null;
      }

      return {
        id: `${pageNumber}-${index}-${trimmed.slice(0, 24)}`,
        text,
        left,
        top,
        width,
        height,
        endX: left + width,
        fontSize: Math.max(fontHeight, 8),
        fontName: normalizePdfFontName(item.fontName, style.fontFamily),
        color: "#111111",
        opacity: 1,
        align: "left" as TextAlign,
        rotation: Math.round((Math.atan2(combined[1], combined[0]) * 180) / Math.PI),
        lineHeight: 1.2,
      } satisfies RawExtractedTextSpan;
    })
    .filter((item): item is RawExtractedTextSpan => item !== null)
    .sort((left, right) => (left.top - right.top) || (left.left - right.left));

  const merged: RawExtractedTextSpan[] = [];
  for (const span of rawSpans) {
    const previous = merged[merged.length - 1];
    if (!previous) {
      merged.push(span);
      continue;
    }

    const sameLine = Math.abs(previous.top - span.top) <= Math.max(previous.height, span.height) * 0.35;
    const sameFont = previous.fontName === span.fontName && Math.abs(previous.fontSize - span.fontSize) <= 1;
    const sameRotation = Math.abs(previous.rotation - span.rotation) <= 2;
    const horizontalGap = span.left - previous.endX;
    const shouldMerge = sameLine && sameFont && sameRotation && horizontalGap >= -2 && horizontalGap <= Math.max(previous.fontSize, span.fontSize) * 1.25;

    if (!shouldMerge) {
      merged.push(span);
      continue;
    }

    const separator = horizontalGap > previous.fontSize * 0.2 ? " " : "";
    previous.text = `${previous.text}${separator}${span.text}`.replace(/\s+/g, " ").trim();
    previous.width = Math.max(previous.endX, span.endX) - previous.left;
    previous.endX = Math.max(previous.endX, span.endX);
    previous.height = Math.max(previous.height, span.height);
    previous.lineHeight = Math.max(previous.lineHeight, span.lineHeight);
  }

  return merged.map(({ endX: _endX, ...span }, index) => ({
    ...span,
    id: `${pageNumber}-merged-${index}`,
  }));
}

// ─── Main component ───────────────────────────────────────────────────────────

const PdfCanvasLayer = forwardRef<PdfCanvasLayerHandle, PdfCanvasLayerProps>(
  function PdfCanvasLayer(
    {
      pdfDocument,
      pageNumber,
      pageRotation,
      activeTool,
      zoom,
      stateManager,
      onDimensionsReady,
      onObjectSelected,
      textProps,
      drawProps,
      shapeProps,
      highlightProps,
      containerWidth,
      onCanvasStateChange,
    },
    ref
  ) {
    const pdfCanvasRef = useRef<HTMLCanvasElement>(null);
    const fabricContainerRef = useRef<HTMLDivElement>(null);
    const fabricCanvasRef = useRef<fabric.Canvas | null>(null);
    const currentPageRef = useRef<number>(pageNumber);
    const dimensionsRef = useRef<PageDimensions | null>(null);
    const previousRotationRef = useRef<number>(0);
    const isDrawingHighlightRef = useRef(false);
    const highlightStartRef = useRef<{ x: number; y: number } | null>(null);
    const highlightPreviewRef = useRef<fabric.Rect | null>(null);
    const extractedTextSpansRef = useRef<ExtractedTextSpan[]>([]);
    const [isRendering, setIsRendering] = useState(false);
    const [viewportSize, setViewportSize] = useState<{ width: number; height: number }>({
      width: 0,
      height: 0,
    });

    const normalizedPageRotation = ((pageRotation % 360) + 360) % 360;

    const _buildViewportTransform = useCallback(
      (rotation: number, unrotatedWidth: number, unrotatedHeight: number): number[] => {
        switch (rotation) {
          case 90:
            return [0, 1, -1, 0, unrotatedHeight, 0];
          case 180:
            return [-1, 0, 0, -1, unrotatedWidth, unrotatedHeight];
          case 270:
            return [0, -1, 1, 0, 0, unrotatedWidth];
          default:
            return [1, 0, 0, 1, 0, 0];
        }
      },
      []
    );

    const _applyViewportRotation = useCallback(
      (unrotatedWidth: number, unrotatedHeight: number) => {
        const fc = fabricCanvasRef.current;
        if (!fc) return;

        fc.setViewportTransform(
          _buildViewportTransform(
            normalizedPageRotation,
            unrotatedWidth,
            unrotatedHeight
          )
        );
        fc.calcOffset();
        fc.requestRenderAll();
      },
      [_buildViewportTransform, normalizedPageRotation]
    );

    const pushHistorySnapshot = useCallback(
      (description: string) => {
        stateManager?.saveSnapshot(description);
      },
      [stateManager]
    );

    const _applyObjectInteractionPolicy = useCallback((obj: fabric.Object) => {
      obj.set({ lockRotation: true });
      const controlsHost = obj as fabric.Object & {
        setControlsVisibility?: (controls: Partial<Record<"mtr", boolean>>) => void;
      };
      controlsHost.setControlsVisibility?.({ mtr: false });
    }, []);

    // ── Expose handle ────────────────────────────────────────────────────────
    useImperativeHandle(ref, () => ({
      saveCurrentPage() {
        _serializePage(pageNumber);
      },
      deleteSelectedObjects() {
        const fc = fabricCanvasRef.current;
        if (!fc) return;
        const active = fc.getActiveObjects();
        if (active.length === 0) return;
        pushHistorySnapshot(`Delete objects on page ${pageNumber}`);
        fc.discardActiveObject();
        active.forEach((obj) => fc.remove(obj));
        fc.requestRenderAll();
        _serializePage(pageNumber);
      },
      deselectAll() {
        fabricCanvasRef.current?.discardActiveObject();
        fabricCanvasRef.current?.requestRenderAll();
      },
      getFabricCanvas() {
        return fabricCanvasRef.current;
      },
    }));

    // ── Serialize canvas state to manager ───────────────────────────────────
    const _serializePage = useCallback(
      (pgNum: number) => {
        const fc = fabricCanvasRef.current;
        const sm = stateManager;
        if (!fc || !sm) return;
        try {
          // Serialize with custom properties so orbType, orbImageData etc. survive round-trips
          const json = fc.toJSON([
            "orbId",
            "orbType",
            "orbImageData",
            "orbShapeType",
            "orbFillOpacity",
            "orbStrokeOpacity",
            "orbHighlightRects",
            "orbSourceSpanId",
            "orbSourceText",
            "orbSourceX",
            "orbSourceY",
            "orbSourceWidth",
            "orbSourceHeight",
            "orbSourceFontSize",
            "orbSourceFontName",
            "orbSourceColor",
            "orbSourceOpacity",
            "orbSourceAlign",
            "orbSourceRotation",
            "orbSourceLineHeight",
          ]);
          sm.commitCanvasObjects(pgNum, (json.objects ?? []) as any[]);
          onCanvasStateChange?.();
        } catch (err) {
          console.error("[PdfCanvasLayer] serialize error:", err);
        }
      },
      [onCanvasStateChange, stateManager]
    );

    // ── Render PDF page ──────────────────────────────────────────────────────
    const renderPdfPage = useCallback(async () => {
      if (!pdfDocument || !pdfCanvasRef.current) return;

      setIsRendering(true);
      try {
        const page = await pdfDocument.getPage(pageNumber);
        const unrotatedViewport = page.getViewport({ scale: 1.0, rotation: 0 });
        const rotatedViewport = page.getViewport({
          scale: 1.0,
          rotation: normalizedPageRotation,
        });
        const fitScale = Math.min(containerWidth / rotatedViewport.width, MAX_AUTO_FIT_SCALE);
        const renderScale = Math.max(fitScale * PDF_RENDER_SCALE_BASE * window.devicePixelRatio, 0.1);
        const viewport = page.getViewport({
          scale: renderScale,
          rotation: normalizedPageRotation,
        });

        const canvas = pdfCanvasRef.current;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        // Size the background canvas to the rendered resolution
        canvas.width = Math.round(viewport.width);
        canvas.height = Math.round(viewport.height);

        // CSS size (display pixels)
        const cssWidth = Math.round(rotatedViewport.width * fitScale);
        const cssHeight = Math.round(rotatedViewport.height * fitScale);
        canvas.style.width = `${cssWidth}px`;
        canvas.style.height = `${cssHeight}px`;
        canvas.style.pointerEvents = "none";

        await page.render({ canvasContext: ctx, viewport }).promise;

        const unrotatedCanvasWidth = Math.round(unrotatedViewport.width * fitScale);
        const unrotatedCanvasHeight = Math.round(unrotatedViewport.height * fitScale);

        const extractedText = await page.getTextContent().then((content) => {
          return extractTextSpansFromContent({ content, fitScale, pageNumber });
        }).catch((error) => {
          console.warn("[PdfCanvasLayer] Text extraction failed:", error);
          return [] as ExtractedTextSpan[];
        });
        extractedTextSpansRef.current = extractedText;

        // Compute dimensions in PDF points using the unrotated coordinate space
        const dims: PageDimensions = {
          widthPts: unrotatedViewport.width,
          heightPts: unrotatedViewport.height,
          canvasWidthPx: unrotatedCanvasWidth,
          canvasHeightPx: unrotatedCanvasHeight,
          renderScale: fitScale,
        };
        dimensionsRef.current = dims;
        setViewportSize({ width: cssWidth, height: cssHeight });
        stateManager?.setPageDimensions(pageNumber, dims);
        onDimensionsReady(dims);

        // Resize Fabric canvas to match
        _resizeFabricCanvas(cssWidth, cssHeight);
        _applyViewportRotation(unrotatedCanvasWidth, unrotatedCanvasHeight);
      } catch (err) {
        console.error("[PdfCanvasLayer] PDF render error:", err);
      } finally {
        setIsRendering(false);
      }
    }, [
      _applyViewportRotation,
      containerWidth,
      normalizedPageRotation,
      pdfDocument,
      pageNumber,
      stateManager,
      onDimensionsReady,
    ]);

    // ── Initialise Fabric.js canvas ──────────────────────────────────────────
    const initFabricCanvas = useCallback(() => {
      const container = fabricContainerRef.current;
      if (!container) return;

      // Destroy existing canvas if reinitialising
      if (fabricCanvasRef.current) {
        fabricCanvasRef.current.dispose();
        fabricCanvasRef.current = null;
      }

      // Create a <canvas> element inside the container
      const el = document.createElement("canvas");
      el.id = `fabric-canvas-p${pageNumber}`;
      container.innerHTML = "";
      container.appendChild(el);

      const fc = new fabric.Canvas(el, {
        selection: true,
        renderOnAddRemove: true,
        preserveObjectStacking: true,
        enableRetinaScaling: true,
        stopContextMenu: true,
      });

      // Set transparent background so PDF shows through
      fc.backgroundColor = "transparent";

      const wrapper = (fc as unknown as { wrapperEl?: HTMLElement }).wrapperEl;
      if (!wrapper) {
        return;
      }
      wrapper.style.position = "absolute";
      wrapper.style.inset = "0";
      wrapper.style.zIndex = "10";
      wrapper.style.width = "100%";
      wrapper.style.height = "100%";

      wrapper.querySelectorAll("canvas").forEach((canvasEl) => {
        const htmlCanvas = canvasEl as HTMLCanvasElement;
        htmlCanvas.style.position = "absolute";
        htmlCanvas.style.inset = "0";
      });

      // Selection handlers
      fc.on("selection:created", (e) => {
        onObjectSelected(e.selected?.[0] ?? null);
      });
      fc.on("selection:updated", (e) => {
        onObjectSelected(e.selected?.[0] ?? null);
      });
      fc.on("selection:cleared", () => {
        onObjectSelected(null);
      });

      // Auto-save on every object modification
      fc.on("object:modified", () => _serializePage(pageNumber));
      fc.on("object:added", (event) => {
        if (event.target) {
          _applyObjectInteractionPolicy(event.target);
        }
        _serializePage(pageNumber);
      });
      fc.on("object:removed", () => _serializePage(pageNumber));

      fabricCanvasRef.current = fc;

      // Restore saved state for this page
      const savedObjects = stateManager?.getCanvasObjects(pageNumber) ?? [];
      if (savedObjects.length > 0) {
        fc.loadFromJSON({ version: "5.3.0", objects: savedObjects }, () => {
          fc.forEachObject((obj) => {
            _applyObjectInteractionPolicy(obj);
          });
          const dims = dimensionsRef.current;
          if (dims) {
            _applyViewportRotation(dims.canvasWidthPx, dims.canvasHeightPx);
          }
          fc.requestRenderAll();
        });
      } else {
        const dims = dimensionsRef.current;
        if (dims) {
          _applyViewportRotation(dims.canvasWidthPx, dims.canvasHeightPx);
        }
      }
    }, [
      _applyObjectInteractionPolicy,
      _applyViewportRotation,
      pageNumber,
      stateManager,
      onObjectSelected,
      _serializePage,
    ]);

    // ── Resize Fabric canvas ─────────────────────────────────────────────────
    const _resizeFabricCanvas = (w: number, h: number) => {
      const fc = fabricCanvasRef.current;
      if (!fc) return;
      fc.setWidth(w);
      fc.setHeight(h);
      const wrapper = (fc as unknown as { wrapperEl?: HTMLElement }).wrapperEl;
      if (wrapper) {
        wrapper.style.width = `${w}px`;
        wrapper.style.height = `${h}px`;
      }
      fc.requestRenderAll();
    };

    const _findExtractedSpanAtPoint = useCallback((x: number, y: number): ExtractedTextSpan | null => {
      let best: ExtractedTextSpan | null = null;
      let bestArea = Number.POSITIVE_INFINITY;

      extractedTextSpansRef.current.forEach((span) => {
        const padding = Math.max(2, Math.min(span.fontSize * 0.18, 6));
        const withinX = x >= span.left - padding && x <= span.left + span.width + padding;
        const withinY = y >= span.top - padding && y <= span.top + span.height + padding;
        if (!withinX || !withinY) {
          return;
        }

        const area = span.width * span.height;
        if (area < bestArea) {
          best = span;
          bestArea = area;
        }
      });

      return best;
    }, []);

    const _activateExistingTextOverlay = useCallback((span: ExtractedTextSpan) => {
      const fc = fabricCanvasRef.current;
      if (!fc) return;

      const existing = fc.getObjects().find((obj) => (obj as any).orbSourceSpanId === span.id);
      if (existing) {
        fc.setActiveObject(existing);
        fc.requestRenderAll();
        if (existing instanceof fabric.Textbox) {
          existing.enterEditing();
          existing.selectAll();
        }
        return;
      }

      pushHistorySnapshot(`Edit extracted text on page ${pageNumber}`);
      const textbox = new fabric.Textbox(span.text, {
        left: span.left,
        top: span.top,
        width: Math.max(span.width, span.fontSize * 0.7),
        height: Math.max(span.height, span.fontSize * 1.1),
        fontSize: span.fontSize,
        fontFamily: span.fontName,
        fill: span.color,
        textAlign: span.align,
        lineHeight: span.lineHeight,
        opacity: span.opacity,
        editable: true,
        splitByGrapheme: false,
        backgroundColor: "rgba(255,255,255,0.02)",
        borderColor: "#ef4444",
        cornerColor: "#ef4444",
      } as fabric.ITextboxOptions);

      (textbox as any).orbType = "existing-text";
      (textbox as any).orbId = Math.random().toString(36).slice(2);
      (textbox as any).orbSourceSpanId = span.id;
      (textbox as any).orbSourceText = span.text;
      (textbox as any).orbSourceX = span.left;
      (textbox as any).orbSourceY = span.top;
      (textbox as any).orbSourceWidth = span.width;
      (textbox as any).orbSourceHeight = span.height;
      (textbox as any).orbSourceFontSize = span.fontSize;
      (textbox as any).orbSourceFontName = span.fontName;
      (textbox as any).orbSourceColor = span.color;
      (textbox as any).orbSourceOpacity = span.opacity;
      (textbox as any).orbSourceAlign = span.align;
      (textbox as any).orbSourceRotation = span.rotation;
      (textbox as any).orbSourceLineHeight = span.lineHeight;
      textbox.set({ angle: span.rotation });

      fc.add(textbox);
      fc.setActiveObject(textbox);
      textbox.enterEditing();
      textbox.selectAll();
      fc.requestRenderAll();
      _serializePage(pageNumber);
    }, [pageNumber, pushHistorySnapshot, _serializePage]);

    // ── Tool mode application ────────────────────────────────────────────────
    useEffect(() => {
      const fc = fabricCanvasRef.current;
      if (!fc) return;

      // Reset all mode flags
      fc.isDrawingMode = false;
      fc.selection = true;
      isDrawingHighlightRef.current = false;

      // Remove existing pointer event listeners (we'll re-add for specific tools)
      fc.off("mouse:down");
      fc.off("mouse:move");
      fc.off("mouse:up");

      switch (activeTool) {
        case "select":
          fc.selection = true;
          fc.forEachObject((obj) => { obj.selectable = true; obj.evented = true; });
          fc.defaultCursor = "default";
          fc.hoverCursor = "move";
          fc.on("mouse:down", (e: fabric.IEvent<MouseEvent>) => {
            if (e.target) {
              const orbType = (e.target as any).orbType ?? e.target.type;
              if ((orbType === "text" || orbType === "existing-text") && e.e.detail >= 2 && e.target instanceof fabric.Textbox) {
                e.target.enterEditing();
                e.target.selectAll();
              }
              pushHistorySnapshot(`Modify object on page ${pageNumber}`);
            }
          });
          break;

        case "edit-text":
          fc.selection = true;
          fc.forEachObject((obj) => { obj.selectable = true; obj.evented = true; });
          fc.defaultCursor = "text";
          fc.hoverCursor = "text";
          fc.on("mouse:down", (e: fabric.IEvent<MouseEvent>) => {
            if (e.target) {
              const orbType = (e.target as any).orbType ?? e.target.type;
              if ((orbType === "text" || orbType === "existing-text") && e.target instanceof fabric.Textbox) {
                fc.setActiveObject(e.target);
                if (e.e.detail >= 2 || orbType === "existing-text") {
                  e.target.enterEditing();
                  e.target.selectAll();
                }
              }
              return;
            }

            const pointer = fc.getPointer(e.e);
            const span = _findExtractedSpanAtPoint(pointer.x, pointer.y);
            if (span) {
              _activateExistingTextOverlay(span);
            }
          });
          break;

        case "draw":
          fc.isDrawingMode = true;
          fc.selection = false;
          fc.freeDrawingBrush.color = drawProps.color;
          fc.freeDrawingBrush.width = drawProps.strokeWidth;
          (fc.freeDrawingBrush as fabric.PencilBrush).strokeLineCap = drawProps.capStyle;
          (fc.freeDrawingBrush as fabric.PencilBrush).strokeLineJoin = drawProps.joinStyle;
          fc.on("mouse:down", () => {
            pushHistorySnapshot(`Draw on page ${pageNumber}`);
          });
          // Tag paths with orbType on creation
          fc.on("path:created", ((event) => {
            const pathEvent = event as { path?: fabric.Path };
            if (pathEvent.path) {
              pathEvent.path.set({
                opacity: drawProps.opacity,
                stroke: drawProps.color,
                strokeWidth: drawProps.strokeWidth,
                strokeLineCap: drawProps.capStyle,
                strokeLineJoin: drawProps.joinStyle,
              });
              (pathEvent.path as any).orbType = "draw";
              (pathEvent.path as any).orbId = Math.random().toString(36).slice(2);
              _serializePage(pageNumber);
            }
          }) as (event: fabric.IEvent<Event>) => void);
          break;

        case "text":
          fc.selection = false;
          fc.defaultCursor = "text";
          fc.on("mouse:down", (e: fabric.IEvent<MouseEvent>) => {
            if (fc.getActiveObject()) return; // allow moving existing text
            pushHistorySnapshot(`Insert text on page ${pageNumber}`);
            const pointer = fc.getPointer(e.e);
            const dims = dimensionsRef.current;
            const defaultW = dims ? dims.canvasWidthPx * 0.4 : 200;
            const textbox = new fabric.Textbox(textProps.text || "Text", {
              left: pointer.x,
              top: pointer.y,
              width: defaultW,
              fontSize: textProps.fontSize,
              fontFamily: textProps.fontName,
              fill: textProps.color,
              fontWeight: textProps.bold ? "bold" : "normal",
              fontStyle: textProps.italic ? "italic" : "normal",
              textAlign: textProps.align,
              lineHeight: textProps.lineHeight,
              opacity: textProps.opacity,
              editable: true,
              splitByGrapheme: false,
            } as fabric.ITextboxOptions);
            (textbox as any).orbType = "text";
            (textbox as any).orbId = Math.random().toString(36).slice(2);
            fc.add(textbox);
            fc.setActiveObject(textbox);
            textbox.enterEditing();
            fc.requestRenderAll();
          });
          break;

        case "highlight":
          fc.selection = false;
          fc.defaultCursor = "crosshair";
          fc.forEachObject((obj) => { obj.selectable = false; obj.evented = false; });
          _installHighlightTool(fc);
          break;

        case "rect":
          fc.selection = false;
          fc.defaultCursor = "crosshair";
          _installShapeTool(fc, "rect");
          break;

        case "circle":
          fc.selection = false;
          fc.defaultCursor = "crosshair";
          _installShapeTool(fc, "circle");
          break;

        case "line":
          fc.selection = false;
          fc.defaultCursor = "crosshair";
          _installShapeTool(fc, "line");
          break;

        case "eraser":
          fc.selection = true;
          fc.defaultCursor = "not-allowed";
          fc.on("mouse:down", (e: fabric.IEvent<MouseEvent>) => {
            const obj = e.target;
            if (obj) {
              pushHistorySnapshot(`Erase object on page ${pageNumber}`);
              fc.remove(obj);
              fc.discardActiveObject();
              fc.requestRenderAll();
            }
          });
          break;

        case "pan":
          fc.selection = false;
          fc.defaultCursor = "grab";
          fc.forEachObject((obj) => { obj.selectable = false; obj.evented = false; });
          break;

        case "image":
        case "signature":
          fc.selection = false;
          fc.defaultCursor = "copy";
          // Handled by file input trigger in PdfEditor.tsx
          break;
      }

      fc.requestRenderAll();
    }, [activeTool, textProps, drawProps, shapeProps, highlightProps, pageNumber, _activateExistingTextOverlay, _findExtractedSpanAtPoint, _serializePage, pushHistorySnapshot]);

    // ── Highlight tool implementation ────────────────────────────────────────
    const _installHighlightTool = (fc: fabric.Canvas) => {
      let startPt: fabric.Point | null = null;
      let preview: fabric.Rect | null = null;

      fc.on("mouse:down", (e: fabric.IEvent<MouseEvent>) => {
        pushHistorySnapshot(`Highlight on page ${pageNumber}`);
        startPt = fc.getPointer(e.e) as unknown as fabric.Point;
        preview = new fabric.Rect({
          left: startPt.x,
          top: startPt.y,
          width: 0,
          height: 0,
          fill: highlightProps.color,
          opacity: highlightProps.opacity,
          selectable: false,
          evented: false,
          stroke: undefined,
          strokeWidth: HIGHLIGHT_RECT_BORDER,
        });
        (preview as any).orbType = "highlight";
        fc.add(preview);
      });

      fc.on("mouse:move", (e: fabric.IEvent<MouseEvent>) => {
        if (!startPt || !preview) return;
        const cur = fc.getPointer(e.e) as unknown as fabric.Point;
        const x = Math.min(startPt.x, cur.x);
        const y = Math.min(startPt.y, cur.y);
        const w = Math.abs(cur.x - startPt.x);
        const h = Math.abs(cur.y - startPt.y);
        preview.set({ left: x, top: y, width: w, height: h });
        fc.requestRenderAll();
      });

      fc.on("mouse:up", () => {
        if (preview) {
          if (preview.width! < 4 || preview.height! < 4) {
            fc.remove(preview);
          } else {
            (preview as any).orbId = Math.random().toString(36).slice(2);
            (preview as any).orbHighlightRects = [
              {
                x0: preview.left!,
                y0: preview.top!,
                x1: preview.left! + preview.width!,
                y1: preview.top! + preview.height!,
              },
            ];
            preview.set({ selectable: true, evented: true });
            _serializePage(pageNumber);
          }
        }
        startPt = null;
        preview = null;
        fc.requestRenderAll();
      });
    };

    // ── Shape tool implementation ────────────────────────────────────────────
    const _installShapeTool = (
      fc: fabric.Canvas,
      shapeType: "rect" | "circle" | "line"
    ) => {
      let startPt: fabric.Point | null = null;
      let preview: fabric.Object | null = null;

      const fillColor =
        shapeType === "line"
          ? "transparent"
          : toCanvasColor(shapeProps.fillColor, shapeProps.fillOpacity);
      const strokeColor = toCanvasColor(shapeProps.strokeColor, shapeProps.strokeOpacity);

      const commonOpts = {
        fill: fillColor,
        stroke: strokeColor,
        strokeWidth: shapeProps.strokeWidth,
        selectable: false,
        evented: false,
        opacity: 1,
      };

      fc.on("mouse:down", (e: fabric.IEvent<MouseEvent>) => {
        pushHistorySnapshot(`Insert ${shapeType} on page ${pageNumber}`);
        startPt = fc.getPointer(e.e) as unknown as fabric.Point;
        if (shapeType === "rect") {
          preview = new fabric.Rect({
            ...commonOpts,
            left: startPt.x,
            top: startPt.y,
            width: 0,
            height: 0,
          });
        } else if (shapeType === "circle") {
          preview = new fabric.Ellipse({
            ...commonOpts,
            left: startPt.x,
            top: startPt.y,
            rx: 0,
            ry: 0,
          });
        } else {
          preview = new fabric.Line([startPt.x, startPt.y, startPt.x, startPt.y], {
            ...commonOpts,
            stroke: strokeColor,
            strokeWidth: shapeProps.strokeWidth,
          });
        }
        (preview as any).orbType = shapeType;
        (preview as any).orbShapeType = shapeType;
        (preview as any).orbFillOpacity = shapeProps.fillOpacity;
        (preview as any).orbStrokeOpacity = shapeProps.strokeOpacity;
        fc.add(preview);
      });

      fc.on("mouse:move", (e: fabric.IEvent<MouseEvent>) => {
        if (!startPt || !preview) return;
        const cur = fc.getPointer(e.e) as unknown as fabric.Point;
        const w = Math.abs(cur.x - startPt.x);
        const h = Math.abs(cur.y - startPt.y);
        const x = Math.min(startPt.x, cur.x);
        const y = Math.min(startPt.y, cur.y);

        if (preview instanceof fabric.Rect) {
          preview.set({ left: x, top: y, width: w, height: h });
        } else if (preview instanceof fabric.Ellipse) {
          preview.set({ left: x, top: y, rx: w / 2, ry: h / 2 });
        } else if (preview instanceof fabric.Line) {
          preview.set({ x2: cur.x, y2: cur.y });
        }
        fc.requestRenderAll();
      });

      fc.on("mouse:up", () => {
        if (preview) {
          (preview as any).orbId = Math.random().toString(36).slice(2);
          preview.set({ selectable: true, evented: true });
          _serializePage(pageNumber);
        }
        startPt = null;
        preview = null;
        fc.requestRenderAll();
      });
    };

    // ── Insert image onto canvas (called from PdfEditor) ─────────────────────
    const insertImage = useCallback(
      (imageDataUrl: string, isSignature = false) => {
        const fc = fabricCanvasRef.current;
        const dims = dimensionsRef.current;
        if (!fc || !dims) return;

        pushHistorySnapshot(`Insert ${isSignature ? "signature" : "image"} on page ${pageNumber}`);

        fabric.Image.fromURL(imageDataUrl, (img) => {
          // Scale image to fit within 40% of page width
          const maxW = dims.canvasWidthPx * 0.4;
          if (img.width && img.width > maxW) {
            const scale = maxW / img.width;
            img.scale(scale);
          }
          img.set({
            left: dims.canvasWidthPx * 0.3,
            top: dims.canvasHeightPx * 0.3,
          });
          (img as any).orbType = isSignature ? "signature" : "image";
          (img as any).orbId = Math.random().toString(36).slice(2);
          // Store base64 data for serialization (src may be object URL)
          (img as any).orbImageData = imageDataUrl;
          fc.add(img);
          fc.setActiveObject(img);
          fc.requestRenderAll();
          _serializePage(pageNumber);
        });
      },
      [pageNumber, _serializePage]
    );

    // Expose insertImage for use by parent via ref
    (fabricContainerRef as any).insertImage = insertImage;

    useEffect(() => {
      const handleInsertImage = (event: Event) => {
        const customEvent = event as CustomEvent<{ dataUrl: string; isSignature?: boolean }>;
        if (!customEvent.detail?.dataUrl) return;
        insertImage(customEvent.detail.dataUrl, customEvent.detail.isSignature);
      };

      document.addEventListener("editor:insert-image", handleInsertImage as EventListener);
      return () => {
        document.removeEventListener("editor:insert-image", handleInsertImage as EventListener);
      };
    }, [insertImage]);

    // ── Effects ──────────────────────────────────────────────────────────────

    // Initialise Fabric canvas once on mount
    useEffect(() => {
      initFabricCanvas();
      return () => {
        _serializePage(currentPageRef.current);
        fabricCanvasRef.current?.dispose();
        fabricCanvasRef.current = null;
      };
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    // Save old page and reinitialize when pageNumber changes
    useEffect(() => {
      if (currentPageRef.current !== pageNumber) {
        _serializePage(currentPageRef.current);
        currentPageRef.current = pageNumber;
        initFabricCanvas();
      }
    }, [pageNumber, initFabricCanvas, _serializePage]);

    useEffect(() => {
      if (!fabricCanvasRef.current) {
        previousRotationRef.current = normalizedPageRotation;
        return;
      }

      if (previousRotationRef.current === normalizedPageRotation) {
        return;
      }

      _serializePage(pageNumber);
      previousRotationRef.current = normalizedPageRotation;
      initFabricCanvas();
    }, [normalizedPageRotation, initFabricCanvas, pageNumber, _serializePage]);

    // Render PDF when document or page changes
    useEffect(() => {
      if (pdfDocument) renderPdfPage();
    }, [pdfDocument, pageNumber, normalizedPageRotation, renderPdfPage]);

    // ── Zoom: apply CSS transform to outer wrapper ───────────────────────────
    const zoomStyle: CSSProperties = {
      transform: `scale(${zoom})`,
      transformOrigin: "top center",
      transition: "transform 0.15s ease",
      willChange: "transform",
    };

    return (
      <div
        className="relative flex justify-center"
        style={{ minHeight: (viewportSize.height || dimensionsRef.current?.canvasHeightPx || 400) * zoom }}
      >
        <div style={zoomStyle} className="relative shadow-2xl rounded-sm overflow-hidden">
          {/* Loading overlay */}
          {isRendering && (
            <div className="absolute inset-0 bg-black/70 flex items-center justify-center z-50">
              <svg className="animate-spin w-8 h-8 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} style={{ filter: "drop-shadow(0 0 6px rgba(255,0,60,0.8))" }}>
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" />
              </svg>
            </div>
          )}

          {/* PDF.js background canvas */}
          <canvas
            ref={pdfCanvasRef}
            className="block bg-white pointer-events-none select-none"
            aria-label={`PDF page ${pageNumber} background`}
          />

          {/* Fabric.js overlay container */}
          <div
            ref={fabricContainerRef}
            className="absolute inset-0 z-10"
            aria-label={`Editing overlay for page ${pageNumber}`}
            style={{ cursor: _getCursorForTool(activeTool), pointerEvents: "auto" }}
          />
        </div>
      </div>
    );
  }
);

// ─── Cursor helper ────────────────────────────────────────────────────────────

function _getCursorForTool(tool: EditorTool): string {
  switch (tool) {
    case "select":    return "default";
    case "edit-text": return "text";
    case "text":      return "text";
    case "highlight": return "crosshair";
    case "draw":      return "crosshair";
    case "image":     return "copy";
    case "signature": return "copy";
    case "rect":      return "crosshair";
    case "circle":    return "crosshair";
    case "line":      return "crosshair";
    case "eraser":    return "cell";
    case "pan":       return "grab";
    default:          return "default";
  }
}

PdfCanvasLayer.displayName = "PdfCanvasLayer";

export default PdfCanvasLayer;
