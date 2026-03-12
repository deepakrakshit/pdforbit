/**
 * editorStateManager.ts — Central State Manager for the PDF Editor
 * =================================================================
 * Manages the complete editor lifecycle:
 *   • Per-page Fabric.js canvas state serialization / deserialization
 *   • Undo/redo history with configurable depth
 *   • Coordinate conversion: canvas pixels ↔ PDF points
 *   • Serialization of editor objects to backend AnyEditorOperation[]
 *   • Page structural operations (rotate, delete, reorder)
 *
 * Usage:
 *   const manager = new EditorStateManager(fileId, fileName, pageCount);
 *   manager.setPageDimensions(1, { widthPts: 595, heightPts: 842, ... });
 *   manager.commitObjects(1, fabricCanvas.toJSON().objects);
 *   const ops = manager.exportOperations();
 *
 * Thread safety: This class is designed for single-threaded browser use.
 * All mutations are synchronous; async work lives in the calling component.
 */

import type {
  AnyEditorOperation,
  DocumentState,
  FontName,
  PageDimensions,
  PageState,
} from "../../../types/editorTypes";

import {
  CANVAS_RENDER_WIDTH_PX,
  MAX_UNDO_HISTORY,
} from "../../../types/editorTypes";

// ─── Tiny ID generator (avoids nanoid dependency) ────────────────────────────
const genId = (): string =>
  Math.random().toString(36).slice(2, 10) + Date.now().toString(36);

// ─── Fabric.js JSON type aliases ─────────────────────────────────────────────
// We type these loosely since fabric.js is loaded externally via CDN / npm
// and its types vary across versions.
interface FabricObjectJSON {
  type: string;
  left: number;
  top: number;
  width: number;
  height: number;
  scaleX: number;
  scaleY: number;
  angle: number;
  opacity: number;
  visible: boolean;
  selectable: boolean;
  // Text-specific
  text?: string;
  fontSize?: number;
  fontFamily?: string;
  fill?: string;
  textAlign?: string;
  fontWeight?: string;
  fontStyle?: string;
  lineHeight?: number;
  // Path-specific
  path?: Array<[string, ...number[]]>;
  stroke?: string;
  strokeWidth?: number;
  strokeLineCap?: string;
  strokeLineJoin?: string;
  // Image-specific
  src?: string;
  // Custom metadata stored in Fabric.js objects
  orbId?: string;
  orbType?: string;
  orbImageData?: string;
  orbShapeType?: string;
  orbFillOpacity?: number;
  orbStrokeOpacity?: number;
  orbHighlightRects?: Array<{ x0: number; y0: number; x1: number; y1: number }>;
  orbSourceSpanId?: string;
  orbSourceText?: string;
  orbSourceX?: number;
  orbSourceY?: number;
  orbSourceWidth?: number;
  orbSourceHeight?: number;
  orbSourceFontSize?: number;
  orbSourceFontName?: string;
  orbSourceColor?: string;
  orbSourceOpacity?: number;
  orbSourceAlign?: "left" | "center" | "right";
  orbSourceRotation?: number;
  orbSourceLineHeight?: number;
}

interface HistorySnapshot {
  timestamp: number;
  description: string;
  pageCanvasJSON: Map<number, FabricObjectJSON[]>;
  deletedPages: Set<number>;
  pageRotations: Map<number, number>;
  pageOrder: number[];
}

// ─── Editor state manager ─────────────────────────────────────────────────────

export class EditorStateManager {
  private readonly fileId: string;
  private readonly fileName: string;
  private readonly totalPages: number;

  /** Per-page dimensions (set after PDF.js renders each page) */
  private pageDimensions: Map<number, PageDimensions> = new Map();

  /** Per-page Fabric.js canvas JSON (the canonical source of truth) */
  private pageCanvasJSON: Map<number, FabricObjectJSON[]> = new Map();

  /** Page structural state */
  private deletedPages: Set<number> = new Set();
  private pageRotations: Map<number, number> = new Map(); // cumulative delta
  private pageOrder: number[]; // 1-indexed page numbers in display order

  /** Undo/redo stacks */
  private undoStack: HistorySnapshot[] = [];
  private redoStack: HistorySnapshot[] = [];

  constructor(fileId: string, fileName: string, totalPages: number) {
    this.fileId = fileId;
    this.fileName = fileName;
    this.totalPages = totalPages;
    this.pageOrder = Array.from({ length: totalPages }, (_, i) => i + 1);

    // Initialise empty canvas state for all pages
    for (let p = 1; p <= totalPages; p++) {
      this.pageCanvasJSON.set(p, []);
    }
  }

  // ─── Dimensions ────────────────────────────────────────────────────────────

  /**
   * Called by PdfCanvasLayer once PDF.js has rendered a page and we know
   * the PDF dimensions and chosen render scale.
   */
  setPageDimensions(pageNumber: number, dims: PageDimensions): void {
    this.pageDimensions.set(pageNumber, dims);
  }

  getPageDimensions(pageNumber: number): PageDimensions | undefined {
    return this.pageDimensions.get(pageNumber);
  }

  computeCanvasDimensions(pageNumber: number, containerWidth: number): {
    canvasWidthPx: number;
    canvasHeightPx: number;
    renderScale: number;
  } {
    const dims = this.pageDimensions.get(pageNumber);
    if (!dims) {
      // Fallback: A4 aspect ratio
      const w = Math.min(containerWidth, CANVAS_RENDER_WIDTH_PX);
      return { canvasWidthPx: w, canvasHeightPx: Math.round(w * 1.4142), renderScale: w / 595 };
    }
    const w = Math.min(containerWidth, CANVAS_RENDER_WIDTH_PX);
    const scale = w / dims.widthPts;
    return {
      canvasWidthPx: w,
      canvasHeightPx: Math.round(dims.heightPts * scale),
      renderScale: scale,
    };
  }

  // ─── Canvas state ──────────────────────────────────────────────────────────

  /**
   * Serializes the current Fabric.js canvas JSON for the given page.
   * Call this before navigating away from a page.
   */
  commitCanvasObjects(pageNumber: number, fabricObjects: FabricObjectJSON[]): void {
    this.pageCanvasJSON.set(pageNumber, fabricObjects);
  }

  /**
   * Returns the Fabric.js JSON objects for a page (to restore canvas state).
   */
  getCanvasObjects(pageNumber: number): FabricObjectJSON[] {
    return this.pageCanvasJSON.get(pageNumber) ?? [];
  }

  // ─── History (undo/redo) ───────────────────────────────────────────────────

  /**
   * Saves a snapshot of the current state to the undo stack.
   * Call this before any mutation.
   */
  saveSnapshot(description: string): void {
    const snapshot = this.captureSnapshot(description);
    this.undoStack.push(snapshot);
    if (this.undoStack.length > MAX_UNDO_HISTORY) {
      this.undoStack.shift();
    }
    // Clear redo stack on new action
    this.redoStack = [];
  }

  undo(): boolean {
    if (this.undoStack.length === 0) return false;
    const current = this.captureSnapshot("redo-checkpoint");
    this.redoStack.push(current);
    const prev = this.undoStack.pop()!;
    this.restoreSnapshot(prev);
    return true;
  }

  redo(): boolean {
    if (this.redoStack.length === 0) return false;
    const current = this.captureSnapshot("undo-checkpoint");
    this.undoStack.push(current);
    const next = this.redoStack.pop()!;
    this.restoreSnapshot(next);
    return true;
  }

  get undoDepth(): number {
    return this.undoStack.length;
  }

  get redoDepth(): number {
    return this.redoStack.length;
  }

  private captureSnapshot(description: string): HistorySnapshot {
    const pageCanvasJSON = new Map<number, FabricObjectJSON[]>();
    for (let p = 1; p <= this.totalPages; p++) {
      const canvasObjects = this.pageCanvasJSON.get(p) ?? [];
      pageCanvasJSON.set(p, this.cloneFabricObjects(canvasObjects));
    }

    return {
      timestamp: Date.now(),
      description,
      pageCanvasJSON,
      deletedPages: new Set(this.deletedPages),
      pageRotations: new Map(this.pageRotations),
      pageOrder: [...this.pageOrder],
    };
  }

  private restoreSnapshot(entry: HistorySnapshot): void {
    this.pageCanvasJSON = new Map();
    entry.pageCanvasJSON.forEach((objects, pageNum) => {
      this.pageCanvasJSON.set(pageNum, this.cloneFabricObjects(objects));
    });
    this.deletedPages = new Set(entry.deletedPages);
    this.pageRotations = new Map(entry.pageRotations);
    this.pageOrder = [...entry.pageOrder];
  }

  private cloneFabricObjects(objects: FabricObjectJSON[]): FabricObjectJSON[] {
    return JSON.parse(JSON.stringify(objects)) as FabricObjectJSON[];
  }

  // ─── Structural page operations ────────────────────────────────────────────

  rotatePage(pageNumber: number, angle: 90 | 180 | 270 | -90 | -180 | -270): void {
    this.saveSnapshot(`Rotate page ${pageNumber}`);
    const existing = this.pageRotations.get(pageNumber) ?? 0;
    this.pageRotations.set(pageNumber, ((existing + angle) % 360 + 360) % 360);
  }

  deletePage(pageNumber: number): void {
    const activePages = this.pageOrder.filter((p) => !this.deletedPages.has(p));
    if (activePages.length <= 1) {
      throw new Error("Cannot delete the last remaining page.");
    }
    this.saveSnapshot(`Delete page ${pageNumber}`);
    this.deletedPages.add(pageNumber);
    this.pageOrder = this.pageOrder.filter((p) => p !== pageNumber);
  }

  reorderPages(newOrder: number[]): void {
    this.saveSnapshot("Reorder pages");
    this.pageOrder = newOrder;
  }

  getPageOrder(): number[] {
    return this.pageOrder.filter((p) => !this.deletedPages.has(p));
  }

  isPageDeleted(pageNumber: number): boolean {
    return this.deletedPages.has(pageNumber);
  }

  getPageRotation(pageNumber: number): number {
    return this.pageRotations.get(pageNumber) ?? 0;
  }

  // ─── Serialization to backend operations ──────────────────────────────────

  /**
   * Converts the complete editor state into a list of AnyEditorOperation[]
   * suitable for sending to the backend ``editor_apply`` processor.
   *
   * Operation ordering:
   *   1. Overlay operations (text, shapes, images) in page order
   *   2. page_rotate operations
   *   3. page_delete operations
   *   4. page_reorder (if page order was changed)
   */
  exportOperations(): AnyEditorOperation[] {
    const operations: AnyEditorOperation[] = [];

    // Phase 1: Overlay operations for each active page
    for (const pageNum of this.pageOrder) {
      if (this.deletedPages.has(pageNum)) continue;
      const dims = this.pageDimensions.get(pageNum);
      if (!dims) continue;

      const fabricObjects = this.pageCanvasJSON.get(pageNum) ?? [];
      for (const obj of fabricObjects) {
        const op = this.fabricObjectToOperation(obj, pageNum, dims);
        if (op) operations.push(op);
      }
    }

    // Phase 2: Page rotate operations
    this.pageRotations.forEach((angleDelta, pageNum) => {
      if (angleDelta !== 0) {
        const normalised = ((angleDelta % 360) + 360) % 360;
        if (normalised === 90 || normalised === 180 || normalised === 270) {
          operations.push({
            type: "page_rotate",
            page: pageNum,
            angle: normalised as 90 | 180 | 270,
          });
        }
      }
    });

    // Phase 3: Page delete operations
    this.deletedPages.forEach((pageNum) => {
      operations.push({ type: "page_delete", page: pageNum });
    });

    // Phase 4: Page reorder — only if order differs from original
    // IMPORTANT: new_order must be 1-based indices into the *surviving* (post-deletion)
    // page list, because the backend applies deletions before reordering.
    // e.g. if pages 1,3,4 survive and the user wants [3,1,4], we emit [2,1,3].
    const survivingOriginalOrder = Array.from({ length: this.totalPages }, (_, i) => i + 1)
      .filter((p) => !this.deletedPages.has(p)); // e.g. [1, 3, 4]
    const currentOrder = this.getPageOrder(); // e.g. [3, 1, 4] after user reorder

    const orderChanged =
      currentOrder.length !== survivingOriginalOrder.length ||
      currentOrder.some((p, i) => p !== survivingOriginalOrder[i]);

    if (orderChanged) {
      // Build a lookup: original page number → 1-based position in surviving list
      const positionByOriginal = new Map<number, number>(
        survivingOriginalOrder.map((p, i) => [p, i + 1])
      );
      const newOrderIndices = currentOrder.map((origPage) => {
        const pos = positionByOriginal.get(origPage);
        if (pos === undefined) {
          throw new Error(`Page ${origPage} is not in the surviving page list.`);
        }
        return pos;
      });
      operations.push({
        type: "page_reorder",
        page: 1, // required by base schema; not semantically meaningful for reorder
        new_order: newOrderIndices,
      });
    }

    return operations;
  }

  // ─── Fabric → Operation conversion ────────────────────────────────────────

  private fabricObjectToOperation(
    obj: FabricObjectJSON,
    pageNum: number,
    dims: PageDimensions,
  ): AnyEditorOperation | null {
    const scale = dims.renderScale;

    // Convert canvas pixel coords to PDF points
    const pdfX = obj.left / scale;
    const pdfY = obj.top / scale;
    const pdfW = (obj.width * (obj.scaleX ?? 1)) / scale;
    const pdfH = (obj.height * (obj.scaleY ?? 1)) / scale;

    const orbType = obj.orbType ?? obj.type;

    switch (orbType) {
      case "text":
      case "i-text":
      case "textbox": {
        if (!obj.text?.trim()) return null;
        const fontName = this.mapFontFamily(obj.fontFamily ?? "helv", obj.fontWeight, obj.fontStyle);
        return {
          type: "text_insert",
          page: pageNum,
          x: pdfX,
          y: pdfY,
          width: Math.max(pdfW, 10),
          height: Math.max(pdfH, 10),
          text: obj.text,
          font_size: (obj.fontSize ?? 16) / scale,
          font_name: fontName,
          color: this.canvasColorToHex(obj.fill ?? "#000000"),
          opacity: obj.opacity ?? 1,
          align: (obj.textAlign as "left" | "center" | "right") ?? "left",
          rotation: obj.angle ?? 0,
          line_height: obj.lineHeight ?? 1.2,
        };
      }

      case "highlight": {
        const rects = obj.orbHighlightRects ?? [];
        if (rects.length === 0) return null;
        return {
          type: "highlight",
          page: pageNum,
          rects: rects.map((r) => [
            r.x0 / scale,
            r.y0 / scale,
            r.x1 / scale,
            r.y1 / scale,
          ] as [number, number, number, number]),
          color: this.canvasColorToHex(obj.fill ?? "#FFFF00"),
          opacity: obj.opacity ?? 0.4,
        };
      }

      case "draw":
      case "path": {
        if (!obj.path) return null;
        // Convert Fabric.js path array to SVG path string in PDF coordinate space
        const pathData = this.fabricPathToSvg(obj.path, obj.left, obj.top, scale);
        if (!pathData) return null;
        return {
          type: "draw",
          page: pageNum,
          path_data: pathData,
          color: this.canvasColorToHex(obj.stroke ?? "#000000"),
          width: (obj.strokeWidth ?? 2) / scale,
          opacity: obj.opacity ?? 1,
          cap_style: (obj.strokeLineCap as "round" | "square" | "butt") ?? "round",
          join_style: (obj.strokeLineJoin as "round" | "miter" | "bevel") ?? "round",
        };
      }

      case "existing-text": {
        const originalText = obj.orbSourceText ?? "";
        const replacementText = obj.text ?? "";
        const replacementRectChanged = this.hasRectChanged(obj, {
          left: obj.orbSourceX ?? obj.left,
          top: obj.orbSourceY ?? obj.top,
          width: obj.orbSourceWidth ?? (obj.width * (obj.scaleX ?? 1)),
          height: obj.orbSourceHeight ?? (obj.height * (obj.scaleY ?? 1)),
        });
        const styleChanged = this.hasExistingTextStyleChanged(obj);
        if (
          replacementText === originalText
          && !replacementRectChanged
          && !styleChanged
        ) {
          return null;
        }

        const fontName = this.mapFontFamily(
          obj.fontFamily ?? obj.orbSourceFontName ?? "helv",
          obj.fontWeight,
          obj.fontStyle,
        );

        return {
          type: "text_replace",
          page: pageNum,
          original_text: originalText,
          replacement_text: replacementText,
          original_x: (obj.orbSourceX ?? obj.left) / scale,
          original_y: (obj.orbSourceY ?? obj.top) / scale,
          original_width: (obj.orbSourceWidth ?? (obj.width * (obj.scaleX ?? 1))) / scale,
          original_height: (obj.orbSourceHeight ?? (obj.height * (obj.scaleY ?? 1))) / scale,
          x: pdfX,
          y: pdfY,
          width: Math.max(pdfW, 10),
          height: Math.max(pdfH, 10),
          font_size: ((obj.fontSize ?? obj.orbSourceFontSize) ?? 16) / scale,
          font_name: fontName,
          color: this.canvasColorToHex(obj.fill ?? obj.orbSourceColor ?? "#000000"),
          opacity: obj.opacity ?? obj.orbSourceOpacity ?? 1,
          align: (obj.textAlign as "left" | "center" | "right") ?? obj.orbSourceAlign ?? "left",
          rotation: obj.angle ?? obj.orbSourceRotation ?? 0,
          line_height: obj.lineHeight ?? obj.orbSourceLineHeight ?? 1.2,
        };
      }

      case "image": {
        const imageData = obj.orbImageData ?? obj.src;
        if (!imageData) return null;
        return {
          type: "image_insert",
          page: pageNum,
          x: pdfX,
          y: pdfY,
          width: Math.max(pdfW, 1),
          height: Math.max(pdfH, 1),
          image_data: imageData,
          opacity: obj.opacity ?? 1,
          rotation: obj.angle ?? 0,
        };
      }

      case "signature": {
        const sigData = obj.orbImageData ?? obj.src;
        if (!sigData) return null;
        return {
          type: "signature_insert",
          page: pageNum,
          x: pdfX,
          y: pdfY,
          width: Math.max(pdfW, 1),
          height: Math.max(pdfH, 1),
          image_data: sigData,
          opacity: obj.opacity ?? 1,
        };
      }

      case "rect":
      case "circle":
      case "line": {
        const shapeType = orbType === "circle" ? "circle" : orbType === "line" ? "line" : "rect";
        return {
          type: "shape_insert",
          page: pageNum,
          x: pdfX,
          y: pdfY,
          width: Math.max(pdfW, 0.5),
          height: Math.max(pdfH, 0.5),
          shape_type: shapeType,
          fill_color: this.canvasColorToHex(obj.fill ?? "#FFFFFF"),
          stroke_color: this.canvasColorToHex(obj.stroke ?? "#000000"),
          stroke_width: (obj.strokeWidth ?? 1) / scale,
          fill_opacity: obj.orbFillOpacity ?? 0,
          stroke_opacity: obj.orbStrokeOpacity ?? 1,
          rotation: obj.angle ?? 0,
        };
      }

      default:
        return null;
    }
  }

  // ─── SVG path conversion ───────────────────────────────────────────────────

  /**
   * Converts a Fabric.js path array (canvas pixels) to an SVG path string
   * with coordinates in PDF points (absolute).
   *
   * Fabric.js path format: [["M", x, y], ["C", cx1, cy1, cx2, cy2, x, y], ...]
   * The coordinates in obj.path are relative to the object's own bounding box,
   * with the object's (left, top) as the reference origin.
   */
  private fabricPathToSvg(
    path: Array<[string, ...number[]]>,
    objLeft: number,
    objTop: number,
    scale: number,
  ): string {
    const parts: string[] = [];
    const topts = (n: number, isX: boolean): number => {
      const offset = isX ? objLeft : objTop;
      return parseFloat(((n + offset) / scale).toFixed(3));
    };
    const n3 = (v: number): string => v.toFixed(3);

    for (const segment of path) {
      const [cmd, ...args] = segment;
      switch (cmd.toUpperCase()) {
        case "M":
          parts.push(`M ${n3(topts(args[0], true))} ${n3(topts(args[1], false))}`);
          break;
        case "L":
          parts.push(`L ${n3(topts(args[0], true))} ${n3(topts(args[1], false))}`);
          break;
        case "C":
          parts.push(
            `C ${n3(topts(args[0], true))} ${n3(topts(args[1], false))} ` +
            `${n3(topts(args[2], true))} ${n3(topts(args[3], false))} ` +
            `${n3(topts(args[4], true))} ${n3(topts(args[5], false))}`
          );
          break;
        case "Q":
          parts.push(
            `Q ${n3(topts(args[0], true))} ${n3(topts(args[1], false))} ` +
            `${n3(topts(args[2], true))} ${n3(topts(args[3], false))}`
          );
          break;
        case "Z":
          parts.push("Z");
          break;
        default:
          break;
      }
    }
    return parts.join(" ");
  }

  // ─── Helpers ───────────────────────────────────────────────────────────────

  private mapFontFamily(family: string, weight?: string, style?: string): FontName {
    const f = (family || "helv").toLowerCase().replace(/[^a-z]/g, "");
    const bold = weight === "bold" || weight === "700";
    const italic = style === "italic" || style === "oblique";
    if (f.startsWith("hel") || f === "helv" || f === "helvetica") {
      if (bold && italic) return "helv-bold-italic";
      if (bold) return "helv-bold";
      if (italic) return "helv-italic";
      return "helv";
    }
    if (f.startsWith("tim") || f.startsWith("times")) {
      if (bold && italic) return "timbi";
      if (bold) return "timb";
      if (italic) return "timi";
      return "timr";
    }
    if (f.startsWith("cou") || f.startsWith("courier")) {
      if (bold && italic) return "courbi";
      if (bold) return "courb";
      if (italic) return "couri";
      return "cour";
    }
    return "helv";
  }

  private canvasColorToHex(color: string): string {
    if (!color || color === "transparent" || color === "rgba(0,0,0,0)") {
      return "#000000";
    }
    if (color.startsWith("#") && color.length === 7) return color;
    // Handle rgb(r, g, b) format
    const rgb = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
    if (rgb) {
      return (
        "#" +
        [rgb[1], rgb[2], rgb[3]]
          .map((v) => parseInt(v).toString(16).padStart(2, "0"))
          .join("")
      );
    }
    return "#000000";
  }
  // ─── State accessors ───────────────────────────────────────────────────────

  getDocumentState(): DocumentState {
    const pages: PageState[] = Array.from({ length: this.totalPages }, (_, i) => {
      const p = i + 1;
      const dims = this.pageDimensions.get(p);
      return {
        pageNumber: p,
        dimensions: dims ?? { widthPts: 595, heightPts: 842, canvasWidthPx: 800, canvasHeightPx: 1131, renderScale: 800 / 595 },
        objects: [],
        deleted: this.deletedPages.has(p),
        rotationDelta: this.pageRotations.get(p) ?? 0,
      };
    });

    return {
      fileId: this.fileId,
      fileName: this.fileName,
      pageCount: this.totalPages,
      currentPage: 1,
      pages,
      pageOrder: this.getPageOrder(),
    };
  }

  hasPageChanges(pageNumber: number): boolean {
    return (this.pageCanvasJSON.get(pageNumber) ?? []).some((obj) => this.isMeaningfulObject(obj));
  }

  isDirty(): boolean {
    for (let p = 1; p <= this.totalPages; p++) {
      if (this.hasPageChanges(p)) return true;
    }
    if (this.deletedPages.size > 0) return true;
    if (this.pageRotations.size > 0) return true;
    const originalOrder = Array.from({ length: this.totalPages }, (_, i) => i + 1);
    return !this.getPageOrder().every((p, i) => p === originalOrder[i]);
  }

  private isMeaningfulObject(obj: FabricObjectJSON): boolean {
    if ((obj.orbType ?? obj.type) !== "existing-text") {
      return true;
    }

    const originalText = obj.orbSourceText ?? "";
    const replacementText = obj.text ?? "";
    return (
      replacementText !== originalText
      || this.hasRectChanged(obj, {
        left: obj.orbSourceX ?? obj.left,
        top: obj.orbSourceY ?? obj.top,
        width: obj.orbSourceWidth ?? (obj.width * (obj.scaleX ?? 1)),
        height: obj.orbSourceHeight ?? (obj.height * (obj.scaleY ?? 1)),
      })
      || this.hasExistingTextStyleChanged(obj)
    );
  }

  private hasExistingTextStyleChanged(obj: FabricObjectJSON): boolean {
    return (
      (obj.fontFamily ?? "helv") !== (obj.orbSourceFontName ?? obj.fontFamily ?? "helv")
      || this.canvasColorToHex(obj.fill ?? obj.orbSourceColor ?? "#000000")
        !== this.canvasColorToHex(obj.orbSourceColor ?? obj.fill ?? "#000000")
      || Math.abs((obj.opacity ?? 1) - (obj.orbSourceOpacity ?? obj.opacity ?? 1)) > 0.001
      || ((obj.textAlign as string | undefined) ?? "left") !== (obj.orbSourceAlign ?? ((obj.textAlign as string | undefined) ?? "left"))
      || Math.abs((obj.angle ?? 0) - (obj.orbSourceRotation ?? obj.angle ?? 0)) > 0.5
      || Math.abs((obj.lineHeight ?? 1.2) - (obj.orbSourceLineHeight ?? obj.lineHeight ?? 1.2)) > 0.01
      || Math.abs((obj.fontSize ?? 16) - (obj.orbSourceFontSize ?? obj.fontSize ?? 16)) > 0.5
    );
  }

  private hasRectChanged(
    obj: FabricObjectJSON,
    original: { left: number; top: number; width: number; height: number },
  ): boolean {
    const currentWidth = (obj.width * (obj.scaleX ?? 1));
    const currentHeight = (obj.height * (obj.scaleY ?? 1));
    return (
      Math.abs(obj.left - original.left) > 0.5
      || Math.abs(obj.top - original.top) > 0.5
      || Math.abs(currentWidth - original.width) > 0.5
      || Math.abs(currentHeight - original.height) > 0.5
    );
  }
}
