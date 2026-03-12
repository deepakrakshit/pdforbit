/**
 * PdfPropertiesPanel.tsx — Context-Aware Properties Panel
 * ========================================================
 * Renders a right-side properties panel that shows controls relevant to:
 *   • The currently active tool (when nothing is selected)
 *   • The selected Fabric.js object (when one is selected)
 *
 * Tool / object types and their property groups:
 *   text     → font, size, color, alignment, opacity, bold/italic
 *   highlight → color, opacity
 *   draw     → color, stroke width, opacity, cap/join style
 *   rect     → fill color, stroke color, stroke width, opacities
 *   circle   → same as rect
 *   line     → stroke color, stroke width, opacity
 *   image    → opacity (no other editable props)
 *   signature → opacity
 *   select   → shows properties of selected object
 *
 * All property changes are applied immediately to the Fabric.js canvas object
 * via the ``onPropertyChange`` callback, which also triggers a state manager save.
 */

"use client";

import React, { useCallback } from "react";

import type {
  DrawProperties,
  EditorTool,
  FontName,
  HighlightProperties,
  ShapeProperties,
  TextProperties,
} from "../../../types/editorTypes";

import { FONT_OPTIONS } from "../../../types/editorTypes";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface PdfPropertiesPanelProps {
  activeTool: EditorTool;
  selectedObjectType: string | null;
  textProps: TextProperties;
  drawProps: DrawProperties;
  shapeProps: ShapeProperties;
  highlightProps: HighlightProperties;
  onTextPropsChange: (props: Partial<TextProperties>) => void;
  onDrawPropsChange: (props: Partial<DrawProperties>) => void;
  onShapePropsChange: (props: Partial<ShapeProperties>) => void;
  onHighlightPropsChange: (props: Partial<HighlightProperties>) => void;
}

// ─── Primitive input components ───────────────────────────────────────────────

interface SectionProps {
  title: string;
  children: React.ReactNode;
}

const Section: React.FC<SectionProps> = ({ title, children }) => (
  <div className="mb-4">
    <h3 className="text-[10px] font-semibold uppercase tracking-widest text-red-500/60 mb-2 px-4">
      {title}
    </h3>
    <div className="space-y-2.5 px-4">{children}</div>
  </div>
);

interface FieldProps {
  label: string;
  children: React.ReactNode;
}

const Field: React.FC<FieldProps> = ({ label, children }) => (
  <div className="flex items-center justify-between gap-2">
    <label className="text-xs text-zinc-500 flex-shrink-0 w-16">{label}</label>
    <div className="flex-1 min-w-0">{children}</div>
  </div>
);

// Colour swatch + hex input
interface ColorFieldProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
}

const ColorField: React.FC<ColorFieldProps> = ({ label, value, onChange }) => (
  <Field label={label}>
    <div className="flex items-center gap-1.5">
      <input
        type="color"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-7 h-7 rounded cursor-pointer border border-red-900/40 bg-transparent
                   hover:border-red-500/60 transition-colors"
        aria-label={`${label} colour picker`}
      />
      <input
        type="text"
        value={value}
        onChange={(e) => {
          const v = e.target.value;
          if (/^#[0-9A-Fa-f]{0,6}$/.test(v)) onChange(v.toUpperCase());
        }}
        maxLength={7}
        className="flex-1 px-2 py-1 text-xs font-mono rounded-md border border-zinc-700
                   bg-zinc-900 text-zinc-200
                   focus:outline-none focus:ring-1 focus:ring-red-500/60 focus:border-red-500/60"
        aria-label={`${label} hex value`}
      />
    </div>
  </Field>
);

// Slider + numeric input combo
interface SliderFieldProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  unit?: string;
  onChange: (v: number) => void;
  formatLabel?: (v: number) => string;
}

const SliderField: React.FC<SliderFieldProps> = ({
  label,
  value,
  min,
  max,
  step = 1,
  unit = "",
  onChange,
  formatLabel,
}) => {
  const display = formatLabel ? formatLabel(value) : `${value}${unit}`;
  return (
    <Field label={label}>
      <div className="flex items-center gap-2">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="flex-1 h-1.5 rounded-full appearance-none bg-zinc-700
                     [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3.5
                     [&::-webkit-slider-thumb]:h-3.5 [&::-webkit-slider-thumb]:rounded-full
                     [&::-webkit-slider-thumb]:bg-red-500 [&::-webkit-slider-thumb]:cursor-pointer
                     [&::-webkit-slider-thumb]:shadow-[0_0_6px_rgba(255,0,60,0.7)]"
          aria-label={label}
        />
        <span className="text-[10px] font-mono text-zinc-500 w-8 text-right tabular-nums">
          {display}
        </span>
      </div>
    </Field>
  );
};

// Select dropdown
interface SelectFieldProps<T extends string> {
  label: string;
  value: T;
  options: { label: string; value: T }[];
  onChange: (v: T) => void;
}

function SelectField<T extends string>({
  label,
  value,
  options,
  onChange,
}: SelectFieldProps<T>) {
  return (
    <Field label={label}>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
        className="w-full px-2 py-1 text-xs rounded-md border border-zinc-700
                   bg-zinc-900 text-zinc-200
                   focus:outline-none focus:ring-1 focus:ring-red-500/60 focus:border-red-500/60"
        aria-label={label}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </Field>
  );
}

// Toggle button group
interface ToggleGroupProps<T extends string> {
  label: string;
  value: T;
  options: { label: string; value: T; icon?: React.ReactNode }[];
  onChange: (v: T) => void;
}

function ToggleGroup<T extends string>({
  label,
  value,
  options,
  onChange,
}: ToggleGroupProps<T>) {
  return (
    <Field label={label}>
      <div className="flex gap-0.5 bg-zinc-900 border border-zinc-800 rounded-md p-0.5">
        {options.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={`
              flex-1 flex items-center justify-center gap-0.5 py-1 px-1.5 rounded text-xs font-medium transition-colors duration-100
              ${value === opt.value
                ? "bg-red-600/20 text-red-400 border border-red-500/40"
                : "text-zinc-500 hover:text-zinc-300"
              }
            `}
            aria-pressed={value === opt.value}
          >
            {opt.icon ?? opt.label}
          </button>
        ))}
      </div>
    </Field>
  );
}

// ─── Tool-specific panels ─────────────────────────────────────────────────────

const TextPanel: React.FC<{
  props: TextProperties;
  onChange: (p: Partial<TextProperties>) => void;
}> = ({ props, onChange }) => (
  <>
    <Section title="Font">
      <SelectField<FontName>
        label="Family"
        value={props.fontName}
        options={FONT_OPTIONS}
        onChange={(v) => onChange({ fontName: v })}
      />
      <SliderField
        label="Size"
        value={props.fontSize}
        min={6}
        max={144}
        step={0.5}
        unit="pt"
        onChange={(v) => onChange({ fontSize: v })}
      />
      <Field label="Style">
        <div className="flex gap-0.5">
          <button
            type="button"
            onClick={() => onChange({ bold: !props.bold })}
            className={`
              w-8 h-7 flex items-center justify-center rounded font-bold text-sm transition-colors
              ${props.bold
                ? "bg-red-600/20 text-red-400 border border-red-500/40"
                : "bg-zinc-900 border border-zinc-700 text-zinc-400 hover:text-zinc-200"
              }
            `}
            aria-pressed={props.bold}
          >
            B
          </button>
          <button
            type="button"
            onClick={() => onChange({ italic: !props.italic })}
            className={`
              w-8 h-7 flex items-center justify-center rounded italic text-sm transition-colors
              ${props.italic
                ? "bg-red-600/20 text-red-400 border border-red-500/40"
                : "bg-zinc-900 border border-zinc-700 text-zinc-400 hover:text-zinc-200"
              }
            `}
            aria-pressed={props.italic}
          >
            I
          </button>
        </div>
      </Field>
      <ToggleGroup<"left" | "center" | "right">
        label="Align"
        value={props.align}
        options={[
          { value: "left",   label: "L", icon: <AlignLeftIcon /> },
          { value: "center", label: "C", icon: <AlignCenterIcon /> },
          { value: "right",  label: "R", icon: <AlignRightIcon /> },
        ]}
        onChange={(v) => onChange({ align: v })}
      />
    </Section>
    <Section title="Appearance">
      <ColorField label="Color" value={props.color} onChange={(v) => onChange({ color: v })} />
      <SliderField
        label="Opacity"
        value={Math.round(props.opacity * 100)}
        min={0}
        max={100}
        step={5}
        formatLabel={(v) => `${v}%`}
        onChange={(v) => onChange({ opacity: v / 100 })}
      />
      <SliderField
        label="Line ht."
        value={props.lineHeight}
        min={0.8}
        max={3.0}
        step={0.05}
        formatLabel={(v) => v.toFixed(2)}
        onChange={(v) => onChange({ lineHeight: v })}
      />
    </Section>
  </>
);

const DrawPanel: React.FC<{
  props: DrawProperties;
  onChange: (p: Partial<DrawProperties>) => void;
}> = ({ props, onChange }) => (
  <>
    <Section title="Stroke">
      <ColorField label="Color" value={props.color} onChange={(v) => onChange({ color: v })} />
      <SliderField
        label="Width"
        value={props.strokeWidth}
        min={0.5}
        max={40}
        step={0.5}
        unit="pt"
        onChange={(v) => onChange({ strokeWidth: v })}
      />
      <SliderField
        label="Opacity"
        value={Math.round(props.opacity * 100)}
        min={0}
        max={100}
        step={5}
        formatLabel={(v) => `${v}%`}
        onChange={(v) => onChange({ opacity: v / 100 })}
      />
    </Section>
    <Section title="Line style">
      <SelectField<"round" | "square" | "butt">
        label="Cap"
        value={props.capStyle}
        options={[
          { label: "Round", value: "round" },
          { label: "Square", value: "square" },
          { label: "Flat", value: "butt" },
        ]}
        onChange={(v) => onChange({ capStyle: v })}
      />
      <SelectField<"round" | "miter" | "bevel">
        label="Join"
        value={props.joinStyle}
        options={[
          { label: "Round", value: "round" },
          { label: "Miter", value: "miter" },
          { label: "Bevel", value: "bevel" },
        ]}
        onChange={(v) => onChange({ joinStyle: v })}
      />
    </Section>
  </>
);

const ShapePanel: React.FC<{
  props: ShapeProperties;
  onChange: (p: Partial<ShapeProperties>) => void;
}> = ({ props, onChange }) => (
  <>
    <Section title="Fill">
      <ColorField
        label="Color"
        value={props.fillColor}
        onChange={(v) => onChange({ fillColor: v })}
      />
      <SliderField
        label="Opacity"
        value={Math.round(props.fillOpacity * 100)}
        min={0}
        max={100}
        step={5}
        formatLabel={(v) => `${v}%`}
        onChange={(v) => onChange({ fillOpacity: v / 100 })}
      />
    </Section>
    <Section title="Stroke">
      <ColorField
        label="Color"
        value={props.strokeColor}
        onChange={(v) => onChange({ strokeColor: v })}
      />
      <SliderField
        label="Width"
        value={props.strokeWidth}
        min={0}
        max={40}
        step={0.5}
        unit="pt"
        onChange={(v) => onChange({ strokeWidth: v })}
      />
      <SliderField
        label="Opacity"
        value={Math.round(props.strokeOpacity * 100)}
        min={0}
        max={100}
        step={5}
        formatLabel={(v) => `${v}%`}
        onChange={(v) => onChange({ strokeOpacity: v / 100 })}
      />
    </Section>
  </>
);

const HighlightPanel: React.FC<{
  props: HighlightProperties;
  onChange: (p: Partial<HighlightProperties>) => void;
}> = ({ props, onChange }) => (
  <Section title="Highlight">
    <ColorField label="Color" value={props.color} onChange={(v) => onChange({ color: v })} />
    <SliderField
      label="Opacity"
      value={Math.round(props.opacity * 100)}
      min={0}
      max={90}
      step={5}
      formatLabel={(v) => `${v}%`}
      onChange={(v) => onChange({ opacity: v / 100 })}
    />
    <div className="pt-1 text-[10px] text-zinc-600 leading-snug">
      Drag to create a highlight rectangle. Right-click to remove.
    </div>
  </Section>
);

// ─── Alignment icons (tiny inline SVGs) ───────────────────────────────────────

const AlignLeftIcon = () => (
  <svg viewBox="0 0 12 10" width={12} height={10} fill="currentColor">
    <rect x="0" y="0" width="12" height="1.5" rx="0.75" />
    <rect x="0" y="3" width="8" height="1.5" rx="0.75" />
    <rect x="0" y="6" width="12" height="1.5" rx="0.75" />
    <rect x="0" y="9" width="6" height="1.5" rx="0.75" />
  </svg>
);
const AlignCenterIcon = () => (
  <svg viewBox="0 0 12 10" width={12} height={10} fill="currentColor">
    <rect x="0" y="0" width="12" height="1.5" rx="0.75" />
    <rect x="2" y="3" width="8" height="1.5" rx="0.75" />
    <rect x="0" y="6" width="12" height="1.5" rx="0.75" />
    <rect x="3" y="9" width="6" height="1.5" rx="0.75" />
  </svg>
);
const AlignRightIcon = () => (
  <svg viewBox="0 0 12 10" width={12} height={10} fill="currentColor">
    <rect x="0" y="0" width="12" height="1.5" rx="0.75" />
    <rect x="4" y="3" width="8" height="1.5" rx="0.75" />
    <rect x="0" y="6" width="12" height="1.5" rx="0.75" />
    <rect x="6" y="9" width="6" height="1.5" rx="0.75" />
  </svg>
);

// ─── Main component ───────────────────────────────────────────────────────────

export const PdfPropertiesPanel: React.FC<PdfPropertiesPanelProps> = ({
  activeTool,
  selectedObjectType,
  textProps,
  drawProps,
  shapeProps,
  highlightProps,
  onTextPropsChange,
  onDrawPropsChange,
  onShapePropsChange,
  onHighlightPropsChange,
}) => {
  // Determine which panel to show: selected object type takes precedence
  const displayType = selectedObjectType ?? activeTool;

  const renderPanel = () => {
    switch (displayType) {
      case "existing-text":
      case "text":
      case "textbox":
      case "i-text":
        return (
          <TextPanel props={textProps} onChange={onTextPropsChange} />
        );

      case "edit-text":
        return (
          <Section title="Edit Text">
            <div className="text-[10px] text-zinc-600 leading-snug">
              Click existing PDF text on the page to extract it into an editable overlay.
              The replacement keeps the detected box and best-effort font metrics.
            </div>
          </Section>
        );

      case "draw":
      case "path":
        return (
          <DrawPanel props={drawProps} onChange={onDrawPropsChange} />
        );

      case "highlight":
        return (
          <HighlightPanel props={highlightProps} onChange={onHighlightPropsChange} />
        );

      case "rect":
      case "circle":
      case "line":
        return (
          <ShapePanel props={shapeProps} onChange={onShapePropsChange} />
        );

      case "image":
      case "signature":
        return (
          <Section title="Image">
            <div className="text-[10px] text-zinc-600 leading-snug">
              Drag to move. Use handles to resize. Hold Shift to maintain aspect ratio.
            </div>
          </Section>
        );

      case "select":
      default:
        return (
          <div className="px-4 pt-2">
            <p className="text-[11px] text-zinc-600 text-center leading-relaxed">
              Select an object on the canvas to edit its properties, or pick a tool from the toolbar.
            </p>
          </div>
        );
    }
  };

  return (
    <aside
      className="min-w-0 w-full bg-zinc-950
                 border-l border-red-900/30
                 flex flex-col overflow-hidden"
      aria-label="Properties panel"
    >
      {/* Header */}
      <div
        className="px-4 py-2 border-b border-red-900/30
                   text-xs font-semibold text-red-500/70 uppercase tracking-wider
                   flex-shrink-0"
      >
        Properties
      </div>

      {/* Panel content */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden py-3 scrollbar-thin scrollbar-thumb-zinc-800">
        {renderPanel()}
      </div>

      {/* Help footer */}
      <div className="flex-shrink-0 px-3 py-2 border-t border-red-900/20">
        <p className="text-[9px] text-zinc-700 text-center leading-snug">
          Del · Remove selected &nbsp;|&nbsp; Esc · Deselect
        </p>
      </div>
    </aside>
  );
};

export default PdfPropertiesPanel;
