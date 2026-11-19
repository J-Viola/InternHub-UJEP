/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      animation: {
        'toast-in': 'slideDown 0.3s ease-out',
      },
      keyframes: {
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      colors: {
        facultyCol: '#41B3BB',
        facultyColLight: '#CFFAFE',
        'yellow-50': '#FEFCE8',
        'green-50': '#ECFDF5',
        'red-50': '#FEF2F2',
        'gray-50': '#F9FAFB'
      },
    },
  },
  plugins: [],
}
