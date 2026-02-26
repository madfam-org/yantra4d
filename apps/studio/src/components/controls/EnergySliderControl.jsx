import React from 'react'

export default function EnergySliderControl({ value, onChange, thermodynamics, language }) {
    if (!thermodynamics) return null

    const tg = thermodynamics.glass_transition_temp || 100
    // Arbitrary upper bound for the slider, e.g., slightly past melting temp
    const maxTemp = (thermodynamics.melting_temp || 200) + 50

    const label = language === 'es' ? 'Simulación de Energía (Digital Twin)' : 'Energy Simulation (Digital Twin)'

    // Determine the current state based on energy (temperature)
    let stateLabel = language === 'es' ? 'Sólido Rígido' : 'Rigid Solid'
    let stateColor = 'text-green-500'

    if (value >= tg) {
        stateLabel = language === 'es' ? 'Deformación Estructural (Colapso)' : 'Structural Deformation (Collapse)'
        stateColor = 'text-red-500'
    } else if (value >= tg * 0.8) {
        stateLabel = language === 'es' ? 'Cerca del Límite de Transición' : 'Approaching Transition Limit'
        stateColor = 'text-yellow-500'
    }

    return (
        <div className="flex flex-col space-y-2 mt-4 p-3 border border-border rounded bg-muted/20">
            <div className="flex justify-between items-center">
                <label className="text-sm font-medium">{label}</label>
                <span className={`text-xs font-bold ${stateColor}`}>{stateLabel}</span>
            </div>

            <div className="flex items-center space-x-3">
                <span className="text-xs text-muted-foreground">0°C</span>
                <input
                    type="range"
                    min={0}
                    max={maxTemp}
                    step={1}
                    value={value || 0}
                    onChange={(e) => onChange('simulated_energy', parseFloat(e.target.value))}
                    className="flex-1 h-2 min-h-[44px] bg-secondary rounded-lg appearance-none cursor-pointer accent-primary [&::-webkit-slider-thumb]:h-11 [&::-webkit-slider-thumb]:w-11 [&::-moz-range-thumb]:h-11 [&::-moz-range-thumb]:w-11"
                />
                <span className="text-xs text-muted-foreground">{maxTemp}°C</span>
            </div>

            <div className="flex justify-between text-xs text-muted-foreground mt-1 px-1">
                <span>Current: {value || 0}°C</span>
                <span>Tg: {tg}°C</span>
            </div>
        </div>
    )
}
