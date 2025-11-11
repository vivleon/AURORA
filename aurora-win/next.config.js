/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  
  async rewrites() {
    return [
      {
        // [수정] /_next/ 파일은 프록시하지 않고,
        // /dash/, /aurora/, /events/, /docs/ 로 시작하는 API 경로만
        // 백엔드(8000)로 정확히 전달합니다.
        source: '/:path(dash|aurora|events|docs|consent)/:slug*', 
        destination: 'http://127.0.0.1:8000/:path/:slug*',
      },
      {
        // 위 :slug*가 없는 단일 경로(예: /aurora/plan)를 위한 규칙
        source: '/:path(dash|aurora|events|docs|consent)', 
        destination: 'http://127.0.0.1:8000/:path',
      }
    ];
  }
};

module.exports = nextConfig;
