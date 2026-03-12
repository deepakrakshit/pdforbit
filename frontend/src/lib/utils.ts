export function fmtBytes(b: number): string {
  if (!b) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(b) / Math.log(1024));
  return `${(b / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

export function escHtml(s: string | number): string {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function parsePages(str: string): number[] | null {
  if (!str || !str.trim()) return null;
  const pages: number[] = [];
  str.split(',').forEach((p) => {
    p = p.trim();
    if (p.includes('-')) {
      const [a, b] = p.split('-').map(Number);
      for (let i = a; i <= b; i++) pages.push(i);
    } else {
      const n = parseInt(p, 10);
      if (!isNaN(n)) pages.push(n);
    }
  });
  return pages.length ? pages : null;
}

export function mkSvgStr(paths: string): string {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${paths}</svg>`;
}

export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
}
