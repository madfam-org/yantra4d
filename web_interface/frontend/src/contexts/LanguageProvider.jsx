import { createContext, useContext, useState, useEffect } from "react"

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
        "anim.preparing": "Preparando animación...",
        "tooltip.gen": "Renderizar el modelo 3D con los parámetros actuales",
        "tooltip.verify": "Ejecutar verificación geométrica del modelo",
        "tooltip.download": "Descargar los archivos STL generados",
        "phase.compiling": "Compilando...",
        "phase.geometry": "Procesando geometría...",
        "phase.cgal": "Procesando CGAL...",
        "phase.rendering": "Renderizando malla...",
        "dialog.render_warning_title": "⚠️ Advertencia de Renderizado Largo",
        "dialog.render_warning_body": "Se estima que este renderizado tardará",
        "dialog.render_warning_note": "La aplicación puede no responder durante este tiempo.",
        "dialog.render_anyway": "Renderizar de Todos Modos",
        "theme.light": "Tema: Claro",
        "theme.dark": "Tema: Oscuro",
        "theme.system": "Tema: Sistema",
        "projects.title": "Proyectos",
        "projects.loading": "Cargando proyectos…",
        "projects.error": "Error al cargar proyectos: ",
        "projects.empty": "No se encontraron proyectos.",
        "projects.empty_cta": "Crea tu primer proyecto →",
        "projects.manifest": "Manifiesto",
        "projects.exports": "Exportaciones",
        // Onboarding
        "onboard.step_upload": "Subir",
        "onboard.step_review": "Revisar",
        "onboard.step_edit": "Editar",
        "onboard.step_save": "Guardar",
        "onboard.upload_title": "Subir Archivos SCAD",
        "onboard.slug_label": "Slug del Proyecto",
        "onboard.slug_placeholder": "mi-proyecto",
        "onboard.drop_text": "Arrastra y suelta archivos .scad aquí, o haz clic para buscar",
        "onboard.browse": "Buscar archivos",
        "onboard.files_selected": "archivo(s) seleccionado(s):",
        "onboard.analyzing": "Analizando...",
        "onboard.analyze_btn": "Analizar Archivos",
        "onboard.review_title": "Resultados del Análisis",
        "onboard.warnings": "Advertencias",
        "onboard.variables": "Variables",
        "onboard.modules": "Módulos",
        "onboard.includes": "Includes",
        "onboard.render_modes": "Modos de render",
        "onboard.none": "ninguno",
        "onboard.back": "Atrás",
        "onboard.edit_manifest": "Editar Manifiesto",
        "onboard.edit_title": "Editar Manifiesto",
        "onboard.project_name": "Nombre del Proyecto",
        "onboard.manifest_json": "Manifiesto JSON",
        "onboard.invalid_json": "JSON inválido",
        "onboard.review_save": "Revisar y Guardar",
        "onboard.save_title": "Guardar Proyecto",
        "onboard.save_summary": "El proyecto {name} ({slug}) se creará con {files} archivo(s) SCAD, {modes} modo(s) y {params} parámetro(s).",
        "onboard.saving": "Guardando...",
        "onboard.create_btn": "Crear Proyecto",
        "onboard.cancel": "Cancelar",
        // Error boundary
        "error.title": "Algo salió mal",
        "error.fallback": "Ocurrió un error inesperado",
        "error.retry": "Intentar de Nuevo",
        // Viewer
        "viewer.hide_axes": "Ocultar ejes",
        "viewer.show_axes": "Mostrar ejes",
        "viewer.pause_anim": "Pausar animación",
        "viewer.play_anim": "Reproducir animación",
        // Nav / SR / Lang
        "nav.projects": "Proyectos",
        "sr.toggle_lang": "Cambiar Idioma",
        "sr.toggle_theme": "Cambiar Tema",
        "lang.switch_to_en": "English",
        "lang.switch_to_es": "Español",
        // Controls
        "ctrl.wireframe": "Estructura",
        "ctrl.click_to_edit": "Clic para editar",
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
        "anim.preparing": "Preparing animation...",
        "tooltip.gen": "Render the 3D model with current parameters",
        "tooltip.verify": "Run geometric verification on the model",
        "tooltip.download": "Download the generated STL files",
        "phase.compiling": "Compiling...",
        "phase.geometry": "Processing geometry...",
        "phase.cgal": "Processing CGAL...",
        "phase.rendering": "Rendering mesh...",
        "dialog.render_warning_title": "⚠️ Long Render Warning",
        "dialog.render_warning_body": "This render is estimated to take",
        "dialog.render_warning_note": "The application may appear unresponsive during this time.",
        "dialog.render_anyway": "Render Anyway",
        "theme.light": "Theme: Light",
        "theme.dark": "Theme: Dark",
        "theme.system": "Theme: System",
        "projects.title": "Projects",
        "projects.loading": "Loading projects…",
        "projects.error": "Failed to load projects: ",
        "projects.empty": "No projects found.",
        "projects.empty_cta": "Create your first project →",
        "projects.manifest": "Manifest",
        "projects.exports": "Exports",
        // Onboarding
        "onboard.step_upload": "Upload",
        "onboard.step_review": "Review",
        "onboard.step_edit": "Edit",
        "onboard.step_save": "Save",
        "onboard.upload_title": "Upload SCAD Files",
        "onboard.slug_label": "Project Slug",
        "onboard.slug_placeholder": "my-project",
        "onboard.drop_text": "Drag & drop .scad files here, or click to browse",
        "onboard.browse": "Browse files",
        "onboard.files_selected": "file(s) selected:",
        "onboard.analyzing": "Analyzing...",
        "onboard.analyze_btn": "Analyze Files",
        "onboard.review_title": "Analysis Results",
        "onboard.warnings": "Warnings",
        "onboard.variables": "Variables",
        "onboard.modules": "Modules",
        "onboard.includes": "Includes",
        "onboard.render_modes": "Render modes",
        "onboard.none": "none",
        "onboard.back": "Back",
        "onboard.edit_manifest": "Edit Manifest",
        "onboard.edit_title": "Edit Manifest",
        "onboard.project_name": "Project Name",
        "onboard.manifest_json": "Manifest JSON",
        "onboard.invalid_json": "Invalid JSON",
        "onboard.review_save": "Review & Save",
        "onboard.save_title": "Save Project",
        "onboard.save_summary": "Project {name} ({slug}) will be created with {files} SCAD file(s), {modes} mode(s), and {params} parameter(s).",
        "onboard.saving": "Saving...",
        "onboard.create_btn": "Create Project",
        "onboard.cancel": "Cancel",
        // Error boundary
        "error.title": "Something went wrong",
        "error.fallback": "An unexpected error occurred",
        "error.retry": "Try Again",
        // Viewer
        "viewer.hide_axes": "Hide axes",
        "viewer.show_axes": "Show axes",
        "viewer.pause_anim": "Pause animation",
        "viewer.play_anim": "Play animation",
        // Nav / SR / Lang
        "nav.projects": "Projects",
        "sr.toggle_lang": "Toggle Language",
        "sr.toggle_theme": "Toggle Theme",
        "lang.switch_to_en": "English",
        "lang.switch_to_es": "Español",
        // Controls
        "ctrl.wireframe": "Wireframe",
        "ctrl.click_to_edit": "Click to edit",
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

    // Sync <html lang> attribute with current language (WCAG 3.1.1)
    useEffect(() => {
        document.documentElement.lang = language
    }, [language])

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
