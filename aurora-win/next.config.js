/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  
  async rewrites() {
    return [
      // [명시적 수정] /dash/, /aurora/ 등 API 경로만 8000번 포트로 전달합니다.
      // Next.js 내부 파일(/_next/)과의 충돌을 방지합니다.
      
      // 1. /dash/kpi/ 등의 복합 경로
      {
        source: '/dash/:path*', 
        destination: 'http://127.0.0.1:8000/dash/:path*',
      },
      {
        source: '/aurora/:path*',
        destination: 'http://127.0.0.1:8000/aurora/:path*',
      },
      {
        source: '/events/:path*',
        destination: 'http://127.0.0.1:8000/events/:path*',
      },
      {
        source: '/docs/:path*', // RAG 문서 미리보기
        destination: 'http://127.0.0.1:8000/docs/:path*',
      },
      {
        source: '/consent/:path*',
        destination: 'http://127.0.0.1:8000/consent/:path*',
      },
      {
        source: '/system_info/:path*', // 환경 정보 API
        destination: 'http://127.0.0.1:8000/system_info/:path*',
      },

      // 2. /dash, /aurora 와 같은 단일 경로 (예: /aurora/plan)
      {
        source: '/:path(dash|aurora|events|docs|consent|system_info)', 
        destination: 'http://127.0.0.1:8000/:path',
      },
    ];
  }
};

module.exports = nextConfig;