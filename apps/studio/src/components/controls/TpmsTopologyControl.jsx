import { Label } from "@/components/ui/label"

const TPMS_OPTIONS = [
    { value: 0, label: "Gyroid", description: "Labyrinthine lattice" },
    { value: 1, label: "Diamond", description: "High stiffness network" },
    { value: 2, label: "Schwarz P", description: "Cubic minimal surface" }
]

export default function TpmsTopologyControl({ param, value, onChange, getLabel, language }) {
    const label = getLabel(param, 'label', language)

    return (
        <div className="space-y-2">
            <Label className="text-sm font-medium">{label}</Label>
            <div className="grid grid-cols-3 gap-2">
                {TPMS_OPTIONS.map((opt) => (
                    <button
                        key={opt.value}
                        type="button"
                        onClick={() => onChange(param.id, [opt.value])}
                        className={`flex flex-col items-center justify-center p-2 rounded-md border text-xs transition-colors ${value === opt.value
                                ? 'bg-primary text-primary-foreground border-primary'
                                : 'bg-background text-muted-foreground border-border hover:border-primary/50'
                            }`}
                        aria-pressed={value === opt.value}
                    >
                        <span className="font-semibold">{opt.label}</span>
                        <span className="text-[10px] opacity-80 mt-1 hidden sm:inline-block text-center shadow-sm">
                            {opt.description}
                        </span>
                    </button>
                ))}
            </div>
        </div>
    )
}
