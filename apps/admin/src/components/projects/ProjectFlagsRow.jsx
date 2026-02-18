import { useState } from 'react'
import { useAdminProjects } from '../../hooks/useAdminProjects'
import { Switch } from '@/components/ui/switch'
import { Loader2, Check, X } from 'lucide-react'

export default function ProjectFlagsRow({ project, isLast }) {
    const { patchFlags } = useAdminProjects()
    const [pending, setPending] = useState(null)
    const [localFlags, setLocalFlags] = useState({
        is_demo: project.is_demo,
        is_hyperobject: project.is_hyperobject,
    })
    const [toast, setToast] = useState(null)

    const toggle = async (flag) => {
        const newVal = !localFlags[flag]
        setPending(flag)
        try {
            await patchFlags(project.slug, { [flag]: newVal })
            setLocalFlags(prev => ({ ...prev, [flag]: newVal }))
            setToast({ type: 'ok', msg: `${flag.replace('is_', '')} → ${newVal ? 'on' : 'off'}` })
        } catch (err) {
            setToast({ type: 'err', msg: err.message })
        } finally {
            setPending(null)
            setTimeout(() => setToast(null), 2500)
        }
    }

    return (
        <tr className={`group transition-colors hover:bg-muted/30 ${!isLast ? 'border-b border-border' : ''} ${localFlags.is_demo ? 'border-l-2 border-l-amber-500' : ''}`}>
            {/* Slug + toast */}
            <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                    <code className="font-mono text-sm font-semibold">{project.slug}</code>
                    {toast && (
                        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium animate-in fade-in slide-in-from-top-1 duration-200
              ${toast.type === 'ok'
                                ? 'bg-green-500/10 text-green-600 dark:text-green-400'
                                : 'bg-destructive/10 text-destructive'
                            }`}>
                            {toast.type === 'ok' ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
                            {toast.msg}
                        </span>
                    )}
                </div>
            </td>

            {/* Demo toggle */}
            <td className="px-4 py-3 text-center">
                {pending === 'is_demo'
                    ? <Loader2 className="mx-auto h-4 w-4 animate-spin text-muted-foreground" />
                    : (
                        <Switch
                            id={`${project.slug}-demo`}
                            checked={localFlags.is_demo}
                            onCheckedChange={() => toggle('is_demo')}
                            aria-label={`Toggle demo for ${project.slug}`}
                            className="data-[state=checked]:bg-amber-500"
                        />
                    )
                }
            </td>

            {/* Hyperobject toggle */}
            <td className="px-4 py-3 text-center">
                {pending === 'is_hyperobject'
                    ? <Loader2 className="mx-auto h-4 w-4 animate-spin text-muted-foreground" />
                    : (
                        <Switch
                            id={`${project.slug}-hyperobject`}
                            checked={localFlags.is_hyperobject}
                            onCheckedChange={() => toggle('is_hyperobject')}
                            aria-label={`Toggle hyperobject for ${project.slug}`}
                            className="data-[state=checked]:bg-violet-500"
                        />
                    )
                }
            </td>

            <td className="px-4 py-3 text-right text-muted-foreground tabular-nums">{project.mode_count ?? '—'}</td>
            <td className="px-4 py-3 text-right text-muted-foreground tabular-nums">{project.parameter_count ?? '—'}</td>
        </tr>
    )
}
