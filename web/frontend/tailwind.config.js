/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  safelist: ['font-numeric'],
  theme: {
    extend: {
      fontFamily: {
        numeric: ['Roboto Mono', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      colors: {
        bgMain: '#0b0f14',
        bgPanel: '#111821',
        card: '#151f2a',
        border: '#253243',
        primary: '#3b82f6',
        up: '#16a34a',
        down: '#ef4444',
        warning: '#f59e0b',
        textMain: '#e5edf6',
        textSub: '#9aa8b6',
        textMute: '#64748b',
      },
    },
  },
  plugins: [],
};
