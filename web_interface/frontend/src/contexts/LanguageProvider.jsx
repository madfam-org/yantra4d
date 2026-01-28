import { createContext, useContext, useState } from "react"

const LanguageProviderContext = createContext()

const translations = {
    es: {
        "app.title": "Tablaco Studio",
        "tab.unit": "Unidad",
        "tab.grid": "Retícula",
        "ctl.size": "Tamaño (mm)",
        "ctl.thick": "Grosor (mm)",
        "ctl.rod_d": "Diámetro Varilla (mm)",
        "ctl.vis": "Visibilidad",
        "ctl.vis.base": "Base",
        "ctl.vis.walls": "Paredes",
        "ctl.vis.mech": "Mecanismo",
        "ctl.grid.dim": "Dimensiones de Retícula",
        "ctl.rows": "Filas",
        "ctl.cols": "Cols",
        "ctl.rod_ext": "Extensión Varilla (mm)",
        "ctl.rod_ext_desc": "Protrusión más allá de los topes (0 = al ras)",
        "btn.gen": "Generar",
        "btn.proc": "Procesando...",
        "btn.verify": "Ejecutar Verificación",
        "log.ready": "Listo.",
        "log.generating": "Generando",
        "log.gen_stl": "STL Generado.",
        "log.error": "Error: ",
        "log.verify": "Verificando diseño...",
        "log.pass": "[PASS] Diseño Verificado.",
        "log.fail": "[FAIL] Se detectaron problemas.",
        "act.download_stl": "Descargar STL",
        "act.export_img": "Exportar Imágenes",
        "view.iso": "Isométrico",
        "view.top": "Superior",
        "view.front": "Frente",
        "view.right": "Derecha",
        "loader.loading": "Renderizando..."
    },
    en: {
        "app.title": "Tablaco Studio",
        "tab.unit": "Unit",
        "tab.grid": "Grid",
        "ctl.size": "Size (mm)",
        "ctl.thick": "Thickness (mm)",
        "ctl.rod_d": "Rod Diameter (mm)",
        "ctl.vis": "Visibility",
        "ctl.vis.base": "Base",
        "ctl.vis.walls": "Walls",
        "ctl.vis.mech": "Mechanism",
        "ctl.grid.dim": "Grid Dimensions",
        "ctl.rows": "Rows",
        "ctl.cols": "Cols",
        "ctl.rod_ext": "Rod Extension (mm)",
        "ctl.rod_ext_desc": "Protrusion beyond stoppers (0 = flush)",
        "btn.gen": "Generate",
        "btn.proc": "Processing...",
        "btn.verify": "Run Verification Suite",
        "log.ready": "Ready.",
        "log.generating": "Generating",
        "log.gen_stl": "Generated STL.",
        "log.error": "Error: ",
        "log.verify": "Verifying design...",
        "log.pass": "[PASS] Design Verified.",
        "log.fail": "[FAIL] Issues detected.",
        "act.download_stl": "Download STL",
        "act.export_img": "Export Images",
        "view.iso": "Isometric",
        "view.top": "Top",
        "view.front": "Front",
        "view.right": "Right",
        "loader.loading": "Rendering..."
    }
}

export function LanguageProvider({
    children,
    defaultLanguage = "es",
    storageKey = "tablaco-lang",
}) {
    const [language, setLanguage] = useState(
        () => localStorage.getItem(storageKey) || defaultLanguage
    )

    const t = (key) => {
        return translations[language][key] || key
    }

    const setLang = (lang) => {
        localStorage.setItem(storageKey, lang)
        setLanguage(lang)
    }

    const value = {
        language,
        setLanguage: setLang,
        t,
    }

    return (
        <LanguageProviderContext.Provider value={value}>
            {children}
        </LanguageProviderContext.Provider>
    )
}

export const useLanguage = () => {
    const context = useContext(LanguageProviderContext)

    if (context === undefined)
        throw new Error("useLanguage must be used within a LanguageProvider")

    return context
}
