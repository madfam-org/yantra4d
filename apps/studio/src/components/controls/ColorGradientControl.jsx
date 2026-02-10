import { Label } from "@/components/ui/label"
import { Tooltip } from "@/components/ui/tooltip"

export default function ColorGradientControl({ param, value, onChange, getLabel, language }) {
    const current = value || { start: '#ff0000', end: '#0000ff' }
    const handleChange = (key, hex) => {
        onChange(param.id, { ...current, [key]: hex })
    }
    return (
        <div className="space-y-2">
            <Tooltip content={getLabel(param, 'tooltip', language)}>
                <Label className="cursor-help">{getLabel(param, 'label', language)}</Label>
            </Tooltip>
            <div className="flex items-center gap-2">
                <div className="flex flex-col gap-1 flex-1">
                    <Label htmlFor={`gradient-start-${param.id}`} className="text-xs text-muted-foreground">
                        {language === 'es' ? 'Inicio' : 'Start'}
                    </Label>
                    <input
                        id={`gradient-start-${param.id}`}
                        type="color"
                        className="w-full h-8 cursor-pointer"
                        value={current.start}
                        onChange={(e) => handleChange('start', e.target.value)}
                    />
                </div>
                <div
                    className="flex-1 h-8 rounded border border-border"
                    style={{ background: `linear-gradient(to right, ${current.start}, ${current.end})` }}
                    aria-label={`Gradient preview: ${current.start} to ${current.end}`}
                />
                <div className="flex flex-col gap-1 flex-1">
                    <Label htmlFor={`gradient-end-${param.id}`} className="text-xs text-muted-foreground">
                        {language === 'es' ? 'Fin' : 'End'}
                    </Label>
                    <input
                        id={`gradient-end-${param.id}`}
                        type="color"
                        className="w-full h-8 cursor-pointer"
                        value={current.end}
                        onChange={(e) => handleChange('end', e.target.value)}
                    />
                </div>
            </div>
        </div>
    )
}
