import { useState } from 'react'
import { LayoutDashboard, ExternalLink, LogOut, Package } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import ProjectList from './projects/ProjectList'
import TablacoLinkPanel from './projects/TablacoLinkPanel'

const VIEWS = [
    { id: 'projects', label: 'Projects', icon: LayoutDashboard },
    { id: 'tablaco', label: 'Tablaco Link', icon: ExternalLink },
]

export default function AdminShell({ auth }) {
    const [activeView, setActiveView] = useState('projects')
    const isProd = import.meta.env.VITE_AUTH_ENABLED === 'true'

    return (
        <div className="flex h-screen overflow-hidden bg-background">
            {/* Sidebar */}
            <aside className="flex w-56 flex-shrink-0 flex-col border-r border-border bg-card">
                {/* Brand */}
                <div className="flex items-center gap-2.5 border-b border-border px-4 py-4">
                    <div className="flex h-7 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground text-xs font-black tracking-tight">
                        Y4D
                    </div>
                    <span className="font-semibold text-sm">Admin</span>
                </div>

                {/* Nav */}
                <nav className="flex flex-1 flex-col gap-1 p-2">
                    {VIEWS.map(({ id, label, icon: Icon }) => (
                        <button
                            key={id}
                            onClick={() => setActiveView(id)}
                            aria-current={activeView === id ? 'page' : undefined}
                            className={`flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors
                ${activeView === id
                                    ? 'bg-primary text-primary-foreground'
                                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                                }`}
                        >
                            <Icon className="h-4 w-4 shrink-0" />
                            {label}
                        </button>
                    ))}
                </nav>

                {/* Footer */}
                <div className="flex items-center gap-2 border-t border-border p-3">
                    <Package className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                    <span className="flex-1 truncate text-xs text-muted-foreground">{auth.user?.email}</span>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 shrink-0"
                        onClick={() => auth.signOut()}
                        title="Sign out"
                    >
                        <LogOut className="h-3.5 w-3.5" />
                    </Button>
                </div>
            </aside>

            {/* Main */}
            <main className="flex flex-1 flex-col overflow-hidden" id="main-content">
                <header className="flex shrink-0 items-center justify-between border-b border-border px-6 py-4">
                    <h1 className="text-lg font-bold">
                        {VIEWS.find(v => v.id === activeView)?.label}
                    </h1>
                    <Badge variant={isProd ? 'default' : 'secondary'}>
                        {isProd ? 'Production' : 'Local Dev'}
                    </Badge>
                </header>

                <div className="flex-1 overflow-y-auto p-6">
                    {activeView === 'projects' && <ProjectList />}
                    {activeView === 'tablaco' && <TablacoLinkPanel />}
                </div>
            </main>
        </div>
    )
}
