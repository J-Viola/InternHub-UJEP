/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
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

