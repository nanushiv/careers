import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        gray: {
          850: "#1a2030",
          950: "#0d1117",
        },
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
export default config;
