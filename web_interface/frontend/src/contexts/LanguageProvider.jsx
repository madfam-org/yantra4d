import { createContext, useContext, useState } from "react"

const LanguageProviderContext = createContext()

const translations = {
    es: {
        "btn.gen": "Generar",
        "btn.proc": "Procesando...",
        "btn.cancel": "Cancelar",
        "btn.verify": "Ejecutar Verificación",
        "btn.reset": "Restablecer Valores",
        "log.ready": "Listo.",
        "log.generating": "Generando",
        "log.gen_stl": "STL Generado.",
        "log.error": "Error: ",
        "log.verify": "Verificando diseño...",
        "log.pass": "[PASS] Diseño Verificado.",
        "log.fail": "[FAIL] Se detectaron problemas.",
        "log.cancelled": "[CANCELADO] Renderizado cancelado.",
        "log.zipping": "Empaquetando partes en ZIP...",
        "log.zip_done": "ZIP descargado.",
        "log.cache_hit": "Cargado desde caché.",
        "log.backend_warn": "Backend no disponible. Verifica que el servidor esté corriendo.",
        "act.download_stl": "Descargar STL",
        "act.export_img": "Exportar Imágenes",
        "act.export_all": "Exportar Todas las Vistas",
        "view.iso": "Isométrico",
        "view.top": "Superior",
        "view.front": "Frente",
        "view.right": "Derecha",
        "loader.loading": "Renderizando...",
        "tooltip.gen": "Renderizar el modelo 3D con los parámetros actuales",
        "tooltip.verify": "Ejecutar verificación geométrica del modelo",
        "tooltip.download": "Descargar los archivos STL generados",
        "phase.compiling": "Compilando...",
        "phase.geometry": "Procesando geometría...",
        "phase.cgal": "Procesando CGAL...",
        "phase.rendering": "Renderizando malla...",
    },
    en: {
        "btn.gen": "Generate",
        "btn.proc": "Processing...",
        "btn.cancel": "Cancel",
        "btn.verify": "Run Verification Suite",
        "btn.reset": "Reset to Defaults",
        "log.ready": "Ready.",
        "log.generating": "Generating",
        "log.gen_stl": "Generated STL.",
        "log.error": "Error: ",
        "log.verify": "Verifying design...",
        "log.pass": "[PASS] Design Verified.",
        "log.fail": "[FAIL] Issues detected.",
        "log.cancelled": "[CANCELLED] Render cancelled.",
        "log.zipping": "Packaging parts into ZIP...",
        "log.zip_done": "ZIP downloaded.",
        "log.cache_hit": "Loaded from cache.",
        "log.backend_warn": "Backend unavailable. Check that the server is running.",
        "act.download_stl": "Download STL",
        "act.export_img": "Export Images",
        "act.export_all": "Export All Views",
        "view.iso": "Isometric",
        "view.top": "Top",
        "view.front": "Front",
        "view.right": "Right",
        "loader.loading": "Rendering...",
        "tooltip.gen": "Render the 3D model with current parameters",
        "tooltip.verify": "Run geometric verification on the model",
        "tooltip.download": "Download the generated STL files",
        "phase.compiling": "Compiling...",
        "phase.geometry": "Processing geometry...",
        "phase.cgal": "Processing CGAL...",
        "phase.rendering": "Rendering mesh...",
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

// eslint-disable-next-line react-refresh/only-export-components
export const useLanguage = () => {
    const context = useContext(LanguageProviderContext)

    if (context === undefined)
        throw new Error("useLanguage must be used within a LanguageProvider")

    return context
}
