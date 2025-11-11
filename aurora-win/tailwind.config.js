/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./webui/**/*.{ts,tsx}" // webui 폴더 인식
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
      // [신규] 자비스 UI 전용 색상 추가
      colors: {
        'hud-bg': '#020A14', // 배경
        'hud-cyan': '#00BFFF', // 메인 텍스트 및 라인
        'hud-cyan-dark': '#007A9E',
        'hud-accent': '#FFA500', // 하이라이트 (예: P95)
        'hud-text': '#E0F8FF', // 본문 텍스트
        'hud-text-muted': '#7A9AAB', // 회색 텍스트
      },
      fontFamily: {
        // [신규] HUD 스타일 폰트 (없을 경우 sans-serif로 폴백)
        'hud': ['"Segoe UI Light"', '"Helvetica Neue"', 'sans-serif'],
      }
    },
  },
  plugins: [require("tailwindcss-animate")],
}
