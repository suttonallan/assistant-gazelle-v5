/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
    "./types/**/*.{js,ts,jsx,tsx}",
    "./hooks/**/*.{js,ts,jsx,tsx}",
    "./config/**/*.{js,ts,jsx,tsx}",
    "./lib/**/*.{js,ts,jsx,tsx}",
  ],
  safelist: [
    // Piano color classes (dynamic, must be safelisted)
    'bg-white',
    'bg-yellow-200',
    'bg-amber-200',
    'bg-green-200',
    'bg-purple-200',
    'border-gray-200',
    'border-yellow-400',
    'border-amber-400',
    'border-green-400',
    'border-purple-400',
    // Hover variants
    'hover:shadow-sm',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
