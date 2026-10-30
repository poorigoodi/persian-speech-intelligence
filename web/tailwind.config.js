/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          950: "rgb(var(--c-navy-950) / <alpha-value>)",
          900: "rgb(var(--c-navy-900) / <alpha-value>)",
          850: "rgb(var(--c-navy-850) / <alpha-value>)",
          800: "rgb(var(--c-navy-800) / <alpha-value>)",
          750: "rgb(var(--c-navy-750) / <alpha-value>)",
          700: "rgb(var(--c-navy-700) / <alpha-value>)",
          600: "rgb(var(--c-navy-600) / <alpha-value>)",
        },
        ink: "rgb(var(--c-ink) / <alpha-value>)",
        mute: "rgb(var(--c-mute) / <alpha-value>)",
        mute2: "rgb(var(--c-mute2) / <alpha-value>)",
        violet: {
          300: "rgb(var(--c-violet-300) / <alpha-value>)",
          400: "rgb(var(--c-violet-400) / <alpha-value>)",
          500: "rgb(var(--c-violet-500) / <alpha-value>)",
          600: "rgb(var(--c-violet-600) / <alpha-value>)",
          800: "rgb(var(--c-violet-800) / <alpha-value>)",
          900: "rgb(var(--c-violet-900) / <alpha-value>)",
        },
        electric: "rgb(var(--c-electric) / <alpha-value>)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(105,59,255,0.35), 0 12px 40px rgba(8,12,40,0.45)",
      },
      keyframes: {
        fadeup: {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        pulsebar: {
          "0%, 100%": { opacity: "0.55" },
          "50%": { opacity: "1" },
        },
      },
      animation: {
        fadeup: "fadeup 0.35s ease-out both",
        pulsebar: "pulsebar 1.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
