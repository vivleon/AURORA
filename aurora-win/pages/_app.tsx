import type { AppProps } from 'next/app'
import './globals.css' // 1. 방금 만든 글로벌 CSS 파일을 불러옵니다.

function MyApp({ Component, pageProps }: AppProps) {
  // 2. 이 컴포넌트가 Dashboard.tsx 등을 렌더링합니다.
  return <Component {...pageProps} />
}

export default MyApp