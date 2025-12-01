/** @type {import('tailwindcss').Config} */
module.exports = {
  // CRÍTICO: Asegúrate de que escanee todos tus templates de Django
  content: [
    "./**/templates/**/*.html",
    "./templates/**/*.html",
    "./static/js/*.js",
  ],
  theme: {
    extend: {},
  },
  

  safelist: [
    'border-red-500/80',
    'border-indigo-500/80',
    'border-cyan-500/80',
    'border-yellow-500/80',
    'border-orange-500/80',
    'border-green-500/80',
    'bg-opacity-75',
    'text-slate-300',
    'bg-cyan-600',
    'border-cyan-600',
    { pattern: /bg-(red|blue|cyan|emerald|gray)-(100|500|600|700|800|900)/, variants: ['hover'] },
    { pattern: /text-(red|blue|cyan|emerald|gray)-(100|500|600|700|800|900)/ },
    { pattern: /border-(red|blue|cyan|emerald|gray)-(100|500|600|700|800|900)/ },
  ],
  plugins: [],
}