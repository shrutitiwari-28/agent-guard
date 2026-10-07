/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: { extend: {
    colors: { bg: "#e7edee", paper: "#f6f8f7", ink: "#14232b", mute: "#5b6b72", rule: "#c4d0d3", clear: "#a9dad5", stain: "#2c2a63", ok: "#2e7d5b", hold: "#c7861b", bad: "#c8325a" },
    fontFamily: { sans: ['"Familjen Grotesk"', "system-ui", "sans-serif"], mono: ['"Martian Mono"', "ui-monospace", "monospace"] },
  } },
  plugins: [],
};
