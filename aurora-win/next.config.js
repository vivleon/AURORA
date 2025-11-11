/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // [필수 추가]
  // UI 서버(3000)가 알지 못하는 모든 경로(예: /dash/*, /aurora/*, /events/*)의
  // 요청을 백엔드 서버(8000)로 전달(proxy)하도록 설정합니다.
  async rewrites() {
    return [
      {
        source: "/:path*",
        destination: "http://127.0.0.1:8000/:path*",
      },
    ];
  }
};

module.exports = nextConfig;
