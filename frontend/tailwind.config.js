/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'SFMono-Regular', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        glass: '0 18px 60px rgb(0 0 0 / 0.34)',
        glow: '0 0 32px rgb(45 212 191 / 0.18)',
      },
    },
  },
  plugins: [],
}
