export interface Category {
  id: string;
  label: string;
}

export const CATS: Category[] = [
  { id: 'all', label: 'All Tools' },
  { id: 'organize', label: 'Organize' },
  { id: 'optimize', label: 'Optimize' },
  { id: 'convert', label: 'Convert' },
  { id: 'edit', label: 'Edit' },
  { id: 'security', label: 'Security' },
  { id: 'ai', label: 'AI Tools' },
];
