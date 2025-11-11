import { useEffect } from 'react'
import { useRouter } from 'next/router'
import DashboardPage from './Dashboard'

// 1. http://localhost:3000/ 로 접속 시
//    /Dashboard 페이지로 자동 리디렉션(이동)하는 코드입니다.
const Home = () => {
  const router = useRouter()
  useEffect(() => {
    router.replace('/Dashboard')
  }, [router])
  return null // 리디렉션 중에는 아무것도 표시하지 않음
}

// 2. 만약 리디렉션 대신 index 페이지에서 직접 대시보드를 보여주고 싶다면,
//    위의 const Home = ... 코드를 모두 지우고 아래 한 줄만 남기세요.
// export default DashboardPage

export default Home