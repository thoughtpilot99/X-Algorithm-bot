/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "media",
  theme: { extend: { fontFamily: { sans: ["Inter", "system-ui", "Segoe UI", "Roboto", "sans-serif"] } } },
  plugins: [],
};
