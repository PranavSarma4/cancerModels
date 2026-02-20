/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bio: {
          50: "#eef9f3",
          100: "#d5f0e3",
          200: "#aee0ca",
          300: "#79c9a9",
          400: "#4ab085",
          500: "#2d9469",
          600: "#1f7754",
          700: "#1a6046",
          800: "#174d39",
          900: "#143f30",
          950: "#0a231b",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
    },
  },
  plugins: [],
};
