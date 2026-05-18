import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        corsair: {
          black: "#050708",
          panel: "#0b0f12",
          card: "#10151b",
          line: "#25303a",
          bronze: "#c8a96a",
          gold: "#f1bd68",
          red: "#b41d3a",
          amber: "#d89535",
          ink: "#151412",
          ivory: "#f7f2ea",
        },
      },
      boxShadow: {
        corsair: "0 24px 80px rgba(0, 0, 0, 0.35)",
        bronze: "0 0 0 1px rgba(200, 169, 106, 0.25), 0 18px 50px rgba(200, 169, 106, 0.10)",
      },
      fontFamily: {
        display: ["ui-serif", "Georgia", "Cambria", "Times New Roman", "serif"],
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [
    function ({ addVariant }: { addVariant: (name: string, value: string) => void }) {
      addVariant("light", ".light &");
    },
  ],
} satisfies Config;
