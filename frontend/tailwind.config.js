/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        base:      '#0b0d12',
        surface:   '#13151c',
        elevated:  '#1a1d27',
        hover:     '#21242f',
        border:    '#262a38',
        accent:    '#6366f1',
        'accent-h':'#818cf8',
        'tx-1':    '#dde1f0',
        'tx-2':    '#7d879e',
        'tx-3':    '#3b4158',
        'sent':    '#2d2b70',
        'recv':    '#1a1d27',
      },
      fontFamily: {
        sans: ['Sora', 'sans-serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.15s ease-out',
        'slide-up': 'slideUp 0.2s ease-out',
        'slide-right': 'slideRight 0.22s ease-out',
      },
      keyframes: {
        fadeIn:    { from: { opacity: 0 }, to: { opacity: 1 } },
        slideUp:   { from: { opacity: 0, transform: 'translateY(8px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        slideRight:{ from: { opacity: 0, transform: 'translateX(-12px)' }, to: { opacity: 1, transform: 'translateX(0)' } },
      },
    },
  },
  plugins: [],
};
