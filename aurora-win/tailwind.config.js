/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./webui/**/*.{ts,tsx}" // [수정] UI 파일이 있는 webui 폴더를 기준으로 설정
  ],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      // (shadcn/ui 기본 설정)
    },
  },
  plugins: [require("tailwindcss-animate")],
}