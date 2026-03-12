/**
 * editorTypes.ts — Shared TypeScript types for the PdfORBIT PDF Editor
 * =====================================================================
 * Mirrors the backend ``app/schemas/editor_operations.py`` Pydantic models.
 * Any change to the backend schema must be reflected here.
 *
 * Coordinate system:
 *   All coordinates are in **PDF points** (1 pt = 1/72 inch).
 *   Origin (0, 0) is the TOP-LEFT corner of the page; y increases downward.
 *   This matches the fitz / PyMuPDF internal coordinate system and the HTML Canvas.
 *
 *   To convert from canvas pixels to PDF points:
 *     pdfX = canvasX / renderScale
 *     pdfY = canvasY / renderScale
 *   where renderScale = canvasWidthPx / pageWidthPts
 */

// ─── Tool identifiers ────────────────────────────────────────────────────────

export type EditorTool =
  | "select"
  | "edit-text"
  | "text"
  | "highlight"
  | "draw"
  | "image"
  | "signature"
  | "rect"
  | "circle"
  | "line"
  | "eraser"
  | "pan";

// ─── Base operation ───────────────────────────────────────────────────────────

export interface EditorOperationBase {
  /** 1-indexed page number */
  page: number;
  type: string;
}

// ─── Overlay operations ───────────────────────────────────────────────────────

export type TextAlign = "left" | "center" | "right";
export type FontName =
  | "helv"
  | "helv-bold"
  | "helv-italic"
  | "helv-bold-italic"
  | "timr"
  | "timb"
  | "timi"
  | "timbi"
  | "cour"
  | "courb"
  | "couri"
  | "courbi"
  | "symb"
  | "zadb";

export interface TextInsertOperation extends EditorOperationBase {
  type: "text_insert";
  /** PDF points from left edge */
  x: number;
  /** PDF points from top edge */
  y: number;
  width: number;
  height: number;
  text: string;
  font_size: number;
  font_name: FontName;
  /** CSS hex colour, e.g. "#FF0000" */
  color: string;
  opacity: number;
  align: TextAlign;
  rotation: number;
  line_height: number;
}

export interface TextReplaceOperation extends EditorOperationBase {
  type: "text_replace";
  original_text: string;
  replacement_text: string;
  original_x: number;
  original_y: number;
  original_width: number;
  original_height: number;
  x: number;
  y: number;
  width: number;
  height: number;
  font_size: number;
  font_name: FontName;
  color: string;
  opacity: number;
  align: TextAlign;
  rotation: number;
  line_height: number;
}

export interface HighlightRect {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

export interface HighlightOperation extends EditorOperationBase {
  type: "highlight";
  /** Array of [x0, y0, x1, y1] tuples in PDF points */
  rects: [number, number, number, number][];
  color: string;
  opacity: number;
}

export type DrawCapStyle = "round" | "square" | "butt";
export type DrawJoinStyle = "round" | "miter" | "bevel";

export interface DrawOperation extends EditorOperationBase {
  type: "draw";
  /**
   * SVG path data with absolute coordinates in PDF points.
   * Supported commands: M, L, C, Q, H, V, Z (uppercase absolute only).
   */
  path_data: string;
  color: string;
  width: number;
  opacity: number;
  cap_style: DrawCapStyle;
  join_style: DrawJoinStyle;
}

export interface ImageInsertOperation extends EditorOperationBase {
  type: "image_insert";
  x: number;
  y: number;
  width: number;
  height: number;
  /** Base64-encoded JPEG or PNG (data-URI prefix accepted) */
  image_data: string;
  opacity: number;
  rotation: number;
}

export interface SignatureInsertOperation extends EditorOperationBase {
  type: "signature_insert";
  x: number;
  y: number;
  width: number;
  height: number;
  /** Base64-encoded PNG with transparent background */
  image_data: string;
  opacity: number;
}

export type ShapeType = "rect" | "circle" | "line";

export interface ShapeInsertOperation extends EditorOperationBase {
  type: "shape_insert";
  x: number;
  y: number;
  width: number;
  height: number;
  shape_type: ShapeType;
  fill_color: string;
  stroke_color: string;
  stroke_width: number;
  fill_opacity: number;
  stroke_opacity: number;
  rotation: number;
}

// ─── Structural operations ────────────────────────────────────────────────────

export type PageRotateAngle = 90 | 180 | 270 | -90 | -180 | -270;

export interface PageRotateOperation extends EditorOperationBase {
  type: "page_rotate";
  angle: PageRotateAngle;
}

export interface PageDeleteOperation extends EditorOperationBase {
  type: "page_delete";
}

export interface PageReorderOperation extends EditorOperationBase {
  type: "page_reorder";
  /** Complete list of 1-indexed original page numbers in desired output order */
  new_order: number[];
}

// ─── Discriminated union ──────────────────────────────────────────────────────

export type AnyEditorOperation =
  | TextInsertOperation
  | TextReplaceOperation
  | HighlightOperation
  | DrawOperation
  | ImageInsertOperation
  | SignatureInsertOperation
  | ShapeInsertOperation
  | PageRotateOperation
  | PageDeleteOperation
  | PageReorderOperation;

// ─── Job request ──────────────────────────────────────────────────────────────

export interface EditorApplyJobRequest {
  file_id: string;
  output_filename: string;
  operations: AnyEditorOperation[];
  /** Canvas pixel width at time of edit (for audit trail) */
  canvas_width?: number;
  canvas_height?: number;
}

// ─── Editor object model (Fabric.js state) ───────────────────────────────────

/**
 * The internal editor object representation, stored per-page.
 * When the user hits "Apply", these are serialized into AnyEditorOperation[].
 */
export interface EditorObjectBase {
  /** Unique client-side ID (nanoid) */
  id: string;
  /** 0-based Fabric.js canvas left position in pixels */
  canvasX: number;
  /** 0-based Fabric.js canvas top position in pixels */
  canvasY: number;
  canvasWidth: number;
  canvasHeight: number;
  scaleX: number;
  scaleY: number;
  rotation: number;
  opacity: number;
  visible: boolean;
  locked: boolean;
}

export interface TextEditorObject extends EditorObjectBase {
  objectType: "text";
  text: string;
  fontSize: number;
  fontName: FontName;
  color: string;
  align: TextAlign;
  bold: boolean;
  italic: boolean;
  lineHeight: number;
}

export interface ExistingTextEditorObject extends EditorObjectBase {
  objectType: "existing-text";
  sourceText: string;
  replacementText: string;
  sourceCanvasX: number;
  sourceCanvasY: number;
  sourceCanvasWidth: number;
  sourceCanvasHeight: number;
  sourceFontSize: number;
  sourceFontName: FontName;
  sourceColor: string;
  sourceAlign: TextAlign;
  sourceLineHeight: number;
  text: string;
  fontSize: number;
  fontName: FontName;
  color: string;
  align: TextAlign;
  bold: boolean;
  italic: boolean;
  lineHeight: number;
}

export interface HighlightEditorObject extends EditorObjectBase {
  objectType: "highlight";
  color: string;
  /** Multiple rects for multi-line text selection */
  rects: HighlightRect[];
}

export interface DrawEditorObject extends EditorObjectBase {
  objectType: "draw";
  /** Fabric.js serialized path data (canvas pixel coords) */
  pathData: string;
  color: string;
  strokeWidth: number;
  capStyle: DrawCapStyle;
  joinStyle: DrawJoinStyle;
}

export interface ImageEditorObject extends EditorObjectBase {
  objectType: "image";
  imageData: string;
}

export interface SignatureEditorObject extends EditorObjectBase {
  objectType: "signature";
  imageData: string;
}

export interface ShapeEditorObject extends EditorObjectBase {
  objectType: "shape";
  shapeType: ShapeType;
  fillColor: string;
  strokeColor: string;
  strokeWidth: number;
  fillOpacity: number;
  strokeOpacity: number;
}

export type AnyEditorObject =
  | TextEditorObject
  | ExistingTextEditorObject
  | HighlightEditorObject
  | DrawEditorObject
  | ImageEditorObject
  | SignatureEditorObject
  | ShapeEditorObject;

// ─── Page state ───────────────────────────────────────────────────────────────

export interface PageDimensions {
  /** Width in PDF points */
  widthPts: number;
  /** Height in PDF points */
  heightPts: number;
  /** Width of the canvas render in pixels */
  canvasWidthPx: number;
  /** Height of the canvas render in pixels */
  canvasHeightPx: number;
  /** Scale factor: canvasWidthPx / widthPts */
  renderScale: number;
}

export interface PageState {
  /** 1-indexed page number */
  pageNumber: number;
  dimensions: PageDimensions;
  /** Editor objects on this page */
  objects: AnyEditorObject[];
  /** Whether this page has been deleted */
  deleted: boolean;
  /** Rotation delta applied in this session */
  rotationDelta: number;
  /** Thumbnail data URL for the pages panel */
  thumbnailDataUrl?: string;
}

export interface DocumentState {
  fileId: string;
  fileName: string;
  pageCount: number;
  /** 1-indexed current page */
  currentPage: number;
  pages: PageState[];
  /** Current page order (1-indexed page numbers) */
  pageOrder: number[];
}

// ─── Editor UI state ──────────────────────────────────────────────────────────

export interface EditorUIState {
  activeTool: EditorTool;
  selectedObjectIds: string[];
  isLoading: boolean;
  isApplying: boolean;
  isDirty: boolean;
  error: string | null;
  /** Current undo stack depth */
  undoDepth: number;
  /** Current redo stack depth */
  redoDepth: number;
}

// ─── Text properties ──────────────────────────────────────────────────────────

export interface TextProperties {
  text: string;
  fontSize: number;
  fontName: FontName;
  color: string;
  align: TextAlign;
  bold: boolean;
  italic: boolean;
  opacity: number;
  lineHeight: number;
}

// ─── Draw properties ──────────────────────────────────────────────────────────

export interface DrawProperties {
  color: string;
  strokeWidth: number;
  opacity: number;
  capStyle: DrawCapStyle;
  joinStyle: DrawJoinStyle;
}

// ─── Shape properties ─────────────────────────────────────────────────────────

export interface ShapeProperties {
  shapeType: ShapeType;
  fillColor: string;
  strokeColor: string;
  strokeWidth: number;
  fillOpacity: number;
  strokeOpacity: number;
}

// ─── Highlight properties ─────────────────────────────────────────────────────

export interface HighlightProperties {
  color: string;
  opacity: number;
}

// ─── Tool properties union ────────────────────────────────────────────────────

export type AnyToolProperties =
  | TextProperties
  | DrawProperties
  | ShapeProperties
  | HighlightProperties;

// ─── History ──────────────────────────────────────────────────────────────────

export interface HistoryEntry {
  timestamp: number;
  description: string;
  pageStates: Map<number, PageState>;
  pageOrder: number[];
}

// ─── Export / apply ───────────────────────────────────────────────────────────

export interface ApplyEditorResult {
  success: boolean;
  jobId?: string;
  downloadUrl?: string;
  error?: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

export const MAX_UNDO_HISTORY = 50;
export const DEFAULT_RENDER_SCALE = 1.5; // canvas pixels per PDF point
export const CANVAS_RENDER_WIDTH_PX = 800; // target canvas width in pixels
export const DEFAULT_FONT_SIZE = 16;
export const DEFAULT_STROKE_WIDTH = 3;
export const DEFAULT_TEXT_COLOR = "#1a1a1a";
export const DEFAULT_HIGHLIGHT_COLOR = "#FFE066";
export const DEFAULT_SHAPE_STROKE_COLOR = "#1a1a1a";
export const DEFAULT_SHAPE_FILL_COLOR = "transparent";
export const FONT_OPTIONS: { label: string; value: FontName }[] = [
  { label: "Helvetica", value: "helv" },
  { label: "Helvetica Bold", value: "helv-bold" },
  { label: "Helvetica Italic", value: "helv-italic" },
  { label: "Times Roman", value: "timr" },
  { label: "Times Bold", value: "timb" },
  { label: "Times Italic", value: "timi" },
  { label: "Courier", value: "cour" },
  { label: "Courier Bold", value: "courb" },
];
