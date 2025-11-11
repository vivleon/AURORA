/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  async rewrites() {
    return [
      {
        // /_next/ (Next.js 내부 경로)와 /favicon.ico 를 제외한 모든 요청을
        source: '/:path((?!_next|favicon.ico).*)', 
        // 백엔드 서버 8000번 포트로 보냅니다.
        destination: 'http://127.0.0.1:8000/:path*',
      },
    ];
  }
};

module.exports = nextConfig;
