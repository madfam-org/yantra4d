import { createContext, useContext, useState } from "react"

const LanguageProviderContext = createContext()

const translations = {
    es: {
        "app.title": "Tablaco Studio",
        "tab.unit": "Unidad",
        "tab.assembly": "Ensamble",
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
        "ctl.colors": "Colores",
        "ctl.color.bottom": "Unidad Inferior",
        "ctl.color.top": "Unidad Superior",
        "ctl.color.rods": "Varillas",
        "ctl.color.stoppers": "Topes",
        "ctl.color.main": "Color",
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
        // Tooltips
        "tooltip.size": "Ancho/alto de cada cubo unitario en milímetros",
        "tooltip.thick": "Grosor de las paredes del cubo",
        "tooltip.rod_d": "Diámetro de las varillas de conexión",
        "tooltip.base": "Mostrar u ocultar la placa base",
        "tooltip.walls": "Mostrar u ocultar las paredes laterales",
        "tooltip.mech": "Mostrar u ocultar el mecanismo de enclavamiento",
        "tooltip.rows": "Número de filas en la retícula",
        "tooltip.cols": "Número de columnas en la retícula",
        "tooltip.rod_ext": "Longitud de varilla que sobresale de los topes",
        "tooltip.gen": "Renderizar el modelo 3D con los parámetros actuales",
        "tooltip.verify": "Ejecutar verificación geométrica del modelo",
        "tooltip.download": "Descargar los archivos STL generados",
        // Progress phases
        "phase.compiling": "Compilando...",
        "phase.geometry": "Procesando geometría...",
        "phase.cgal": "Procesando CGAL...",
        "phase.rendering": "Renderizando malla...",
    },
    en: {
        "app.title": "Tablaco Studio",
        "tab.unit": "Unit",
        "tab.assembly": "Assembly",
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
        "ctl.colors": "Colors",
        "ctl.color.bottom": "Bottom Unit",
        "ctl.color.top": "Top Unit",
        "ctl.color.rods": "Rods",
        "ctl.color.stoppers": "Stoppers",
        "ctl.color.main": "Color",
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
        // Tooltips
        "tooltip.size": "Width/height of each unit cube in millimeters",
        "tooltip.thick": "Wall thickness of the cube",
        "tooltip.rod_d": "Diameter of connecting rods",
        "tooltip.base": "Show or hide the base plate",
        "tooltip.walls": "Show or hide the side walls",
        "tooltip.mech": "Show or hide the interlocking mechanism",
        "tooltip.rows": "Number of rows in the grid",
        "tooltip.cols": "Number of columns in the grid",
        "tooltip.rod_ext": "Rod length protruding beyond stoppers",
        "tooltip.gen": "Render the 3D model with current parameters",
        "tooltip.verify": "Run geometric verification on the model",
        "tooltip.download": "Download the generated STL files",
        // Progress phases
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

export const useLanguage = () => {
    const context = useContext(LanguageProviderContext)

    if (context === undefined)
        throw new Error("useLanguage must be used within a LanguageProvider")

    return context
}
