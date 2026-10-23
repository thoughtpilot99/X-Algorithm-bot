/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  // Dark when the OS asks for it unless the viewer chose light, or when the viewer chose dark.
  darkMode: ["variant", ["@media (prefers-color-scheme: dark) { &:not([data-theme=light] *) }", "&:is([data-theme=dark] *)"]],
  theme: { extend: { fontFamily: { sans: ["IBM Plex Sans", "Segoe UI", "system-ui", "sans-serif"], mono: ["IBM Plex Mono", "ui-monospace", "monospace"] } } },
  plugins: [],
};
