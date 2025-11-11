/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // [필수 수정]
  // Pages Router(현재 구조)는 'rewrites' 대신 'proxy' 설정을 사용해야
  // API 요청(예: /dash/*)을 백엔드(8000)로 올바르게 전달합니다.
  async rewrites() {
    return [
      {
        // /dash/, /aurora/, /events/, /docs/ 로 시작하는 모든 API 요청을
        source: '/:path((?!_next|favicon.ico).*)', 
        // 실제 백엔드 서버인 8000번 포트로 보냅니다.
        destination: 'http://127.0.0.1:8000/:path*',
      },
    ];
  }
};

module.exports = nextConfig;
