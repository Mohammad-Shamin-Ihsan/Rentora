/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  theme: {
    extend: {
      colors: {
        rentora: {
          bg:        '#0a0a0f',
          surface:   '#12121a',
          border:    '#1e1e2e',
          primary:   '#8b5cf6',
          secondary: '#ec4899',
          accent:    '#f97316',
          text:      '#e2e8f0',
          muted:     '#64748b',
        }
      }
    },
  },
  plugins: [],
}