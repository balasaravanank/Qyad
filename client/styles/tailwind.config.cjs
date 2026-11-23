module.exports = {
  theme: {
    extend: {
      fontFamily: { sans: ['Be Vietnam Pro', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'] },
      colors: {
        brand: {
          50:  '#FCF3EE', 100: '#F9E5DA', 200: '#F2C9B5', 300: '#E9A587',
          400: '#E08466', 500: '#D97757', 600: '#C25E3F', 700: '#A04A31',
          800: '#7F3D29', 900: '#62301F', 950: '#3E2015',
        }
      },
      boxShadow: {
        card: '0 1px 2px rgba(60,45,35,.04), 0 1px 3px rgba(60,45,35,.06)',
        pop: '0 12px 32px -8px rgba(60,45,35,.16), 0 4px 12px rgba(60,45,35,.07)',
      },
    }
  }
, content:["./public/static/*.js","./public/index.html"]
}