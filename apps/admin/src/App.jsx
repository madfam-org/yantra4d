import { useJanuaAuth } from './hooks/useJanuaAuth'
import AuthGuard from './components/auth/AuthGuard'
import AdminShell from './components/AdminShell'

export default function App() {
    const auth = useJanuaAuth()
    return <AuthGuard auth={auth}><AdminShell auth={auth} /></AuthGuard>
}
