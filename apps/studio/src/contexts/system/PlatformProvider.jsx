import { createContext, useContext, useState, useEffect } from 'react'
import { apiFetch } from '../../services/core/apiClient'
import { getApiBase } from '../../services/core/backendDetection'

const PlatformContext = createContext({
    platformName: 'Yantra4D',
    platformLogo: '/logo.png',
    loading: true
})

// eslint-disable-next-line react-refresh/only-export-components
export function usePlatform() {
    return useContext(PlatformContext)
}

export function PlatformProvider({ children }) {
    const [state, setState] = useState({
        platformName: 'Yantra4D',
        platformLogo: '/logo.png',
        loading: true
    })

    useEffect(() => {
        let mounted = true
        async function fetchConfig() {
            try {
                const res = await apiFetch(`${getApiBase()}/api/config/client`)
                if (res.ok) {
                    const data = await res.json()
                    if (mounted) {
                        setState({
                            platformName: data.platformName || 'Yantra4D',
                            platformLogo: data.platformLogo || '/logo.png',
                            loading: false
                        })
                        return // Skip fallback
                    }
                }
            } catch (err) {
                console.warn('Failed to fetch platform config, falling back to defaults:', err)
            }

            // Fallback defaults on error
            if (mounted) {
                setState({
                    platformName: 'Yantra4D',
                    platformLogo: '/logo.png',
                    loading: false
                })
            }
        }

        fetchConfig()
        return () => { mounted = false }
    }, [])

    return (
        <PlatformContext.Provider value={state}>
            {children}
        </PlatformContext.Provider>
    )
}
