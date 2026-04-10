import { Label } from "@/components/ui/label"
import { Tooltip } from "@/components/ui/tooltip"

interface GradientValue {
    start: string
    end: string
}

interface ColorGradientParam {
    id: string
    [key: string]: unknown
}

interface ColorGradientControlProps {
    param: ColorGradientParam
    value: GradientValue | undefined
    onChange: (name: string, gradientValue: GradientValue) => void
    getLabel: (obj: Record<string, unknown> | null | undefined, key: string, lang: string) => string
    language: string
}

export default function ColorGradientControl({ param, value, onChange, getLabel, language }: ColorGradientControlProps) {
    const current = value || { start: '#ff0000', end: '#0000ff' }
    const handleChange = (key: 'start' | 'end', hex: string) => {
        onChange(param.id, { ...current, [key]: hex })
    }
    return (
        <div className="space-y-2">
            <Tooltip content={getLabel(param as unknown as Record<string, unknown>, 'tooltip', language)}>
                <Label className="cursor-help">{getLabel(param as unknown as Record<string, unknown>, 'label', language)}</Label>
            </Tooltip>
            <div className="flex items-center gap-2">
                <div className="flex flex-col gap-1 flex-1">
                    <Label htmlFor={`gradient-start-${param.id}`} className="text-xs text-muted-foreground">
                        {language === 'es' ? 'Inicio' : 'Start'}
                    </Label>
                    <input
                        id={`gradient-start-${param.id}`}
                        type="color"
                        className="w-full h-11 md:h-8 min-h-[44px] md:min-h-0 cursor-pointer"
                        value={current.start}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleChange('start', e.target.value)}
                    />
                </div>
                <div
                    className="flex-1 h-10 md:h-8 rounded border border-border"
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
                        className="w-full h-11 md:h-8 min-h-[44px] md:min-h-0 cursor-pointer"
                        value={current.end}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleChange('end', e.target.value)}
                    />
                </div>
            </div>
        </div>
    )
}
