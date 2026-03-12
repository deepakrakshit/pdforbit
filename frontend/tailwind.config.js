/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ['Orbitron', 'sans-serif'],
        body: ['Barlow Condensed', 'sans-serif'],
        mono: ['DM Mono', 'monospace'],
      },
      colors: {
        red: {
          DEFAULT: '#FF2020',
          hover: '#e01818',
          dim: 'rgba(255,32,32,0.10)',
          glow: 'rgba(255,32,32,0.35)',
          border: 'rgba(255,32,32,0.28)',
        },
        orange: '#FF8020',
        black: '#050505',
        surface: '#0a0a0d',
        card: '#0e0e12',
        'card-hover': '#141418',
        border: '#1a1a22',
        'border-light': '#242432',
        'text-dim': '#a0a0b8',
        muted: '#55556a',
        green: '#22c55e',
        amber: '#f59e0b',
        cyan: '#40ffee',
      },
    },
  },
  plugins: [],
};
