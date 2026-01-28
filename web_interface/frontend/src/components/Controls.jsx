import React from 'react'

export default function Controls({ params, setParams }) {
    const handleChange = (e) => {
        const { name, value, type, checked } = e.target
        setParams(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : parseFloat(value)
        }))
    }

    return (
        <div className="control-group">
            <label>Size (mm): {params.size}</label>
            <input
                type="range"
                name="size"
                min="10"
                max="50"
                step="0.5"
                value={params.size}
                onChange={handleChange}
            />

            <label>Thickness (mm): {params.thick}</label>
            <input
                type="range"
                name="thick"
                min="1"
                max="10"
                step="0.1"
                value={params.thick}
                onChange={handleChange}
            />

            <label>Visibility:</label>
            <div className="checkbox-group">
                <input
                    type="checkbox"
                    name="show_base"
                    checked={params.show_base}
                    onChange={handleChange}
                />
                <span>Base</span>
            </div>
            <div className="checkbox-group">
                <input
                    type="checkbox"
                    name="show_walls"
                    checked={params.show_walls}
                    onChange={handleChange}
                />
                <span>Walls</span>
            </div>
            <div className="checkbox-group">
                <input
                    type="checkbox"
                    name="show_mech"
                    checked={params.show_mech}
                    onChange={handleChange}
                />
                <span>Mechanism</span>
            </div>
        </div>
    )
}
