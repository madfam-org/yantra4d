import { createContext, useContext, useState, useEffect, useMemo, useCallback } from "react"
import ptLocale from '../locales/pt.json'
import frLocale from '../locales/fr.json'
import deLocale from '../locales/de.json'
import zhLocale from '../locales/zh.json'

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
        "projects.search": "Buscar proyectos…",
        "projects.no_results": "No se encontraron resultados.",
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
        "onboard.raw_json": "JSON sin formato",
        "onboard.structured_view": "Vista estructurada",
        "onboard.modes_label": "Modos",
        "onboard.params_label": "Parámetros",
        "onboard.parts_label": "Partes y colores",
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
        // Share & Undo/Redo
        "act.share": "Compartir configuración",
        "act.share_copied": "¡Enlace copiado!",
        "act.undo": "Deshacer",
        "act.redo": "Rehacer",
        "act.format": "Formato",
        "act.download_scad": "Descargar SCAD",
        // Auth
        "auth.sign_in": "Iniciar sesión",
        "auth.sign_out": "Cerrar sesión",
        "auth.sign_in_to_download": "Inicia sesión para descargar",
        "auth.signed_in_as": "Sesión como",
        // Print estimation
        "print.title": "Estimación de Impresión",
        "print.material": "Material",
        "print.infill": "Relleno",
        "print.time": "Tiempo",
        "print.weight": "Peso",
        "print.length": "Filamento",
        "print.cost": "Costo",
        "platform.powered_by": "desarrollado con Yantra4D",
        // Status chip
        "status.rendering": "Renderizando…",
        "status.ready": "Listo",
        "status.failed": "Falló",
        "status.retry": "Reintentar",
        // Toasts
        "toast.share_failed": "No se pudo copiar el enlace",
        "toast.cache_hit": "Cargado desde caché",
        "toast.export_started": "Exportación iniciada…",
        "toast.export_done": "Exportación completada",
        "toast.render_failed": "Error al renderizar",
        // BOM
        "bom.title": "Lista de Materiales",
        "bom.item": "Elemento",
        "bom.qty": "Cant.",
        "bom.unit": "Unidad",
        // Assembly
        "assembly.title": "Instrucciones de Ensamblaje",
        "assembly.step": "Paso",
        "assembly.prev": "Paso anterior",
        "assembly.next": "Siguiente paso",
        // Comparison
        "compare.title": "Comparación",
        "compare.empty": "Sin variaciones para comparar",
        "compare.add_current": "Agregar actual",
        "compare.sync_camera": "Sincronizar cámara",
        // Datasheet
        "datasheet.generate": "Generar ficha técnica",
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
        "projects.search": "Search projects…",
        "projects.no_results": "No projects match your search.",
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
        "onboard.raw_json": "Raw JSON",
        "onboard.structured_view": "Structured view",
        "onboard.modes_label": "Modes",
        "onboard.params_label": "Parameters",
        "onboard.parts_label": "Parts & Colors",
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
        // Share & Undo/Redo
        "act.share": "Share configuration",
        "act.share_copied": "Link copied!",
        "act.undo": "Undo",
        "act.redo": "Redo",
        "act.format": "Format",
        "act.download_scad": "Download SCAD",
        // Auth
        "auth.sign_in": "Sign in",
        "auth.sign_out": "Sign out",
        "auth.sign_in_to_download": "Sign in to download",
        "auth.signed_in_as": "Signed in as",
        // Print estimation
        "print.title": "Print Estimate",
        "print.material": "Material",
        "print.infill": "Infill",
        "print.time": "Time",
        "print.weight": "Weight",
        "print.length": "Filament",
        "print.cost": "Cost",
        "platform.powered_by": "powered by Yantra4D",
        // Status chip
        "status.rendering": "Rendering…",
        "status.ready": "Ready",
        "status.failed": "Failed",
        "status.retry": "Retry",
        // Toasts
        "toast.share_failed": "Failed to copy link",
        "toast.cache_hit": "Loaded from cache",
        "toast.export_started": "Export started…",
        "toast.export_done": "Export completed",
        "toast.render_failed": "Render failed",
        // BOM
        "bom.title": "Bill of Materials",
        "bom.item": "Item",
        "bom.qty": "Qty",
        "bom.unit": "Unit",
        // Assembly
        "assembly.title": "Assembly Instructions",
        "assembly.step": "Step",
        "assembly.prev": "Previous step",
        "assembly.next": "Next step",
        // Comparison
        "compare.title": "Comparison",
        "compare.empty": "No variations to compare",
        "compare.add_current": "Add current",
        "compare.sync_camera": "Sync camera",
        // Datasheet
        "datasheet.generate": "Generate Datasheet",
    }
}

// Supplementary locales — keys missing here fall back to English
const supplementaryLocales = { pt: ptLocale, fr: frLocale, de: deLocale, zh: zhLocale }

// Merge: inline translations take priority, then supplementary, then fallback to en
function resolveTranslation(lang, key) {
    if (translations[lang]?.[key]) return translations[lang][key]
    if (supplementaryLocales[lang]?.[key]) return supplementaryLocales[lang][key]
    return translations.en?.[key] || key
}

export function LanguageProvider({
    children,
    defaultLanguage = "es",
    storageKey = "yantra4d-lang",
}) {
    const [language, setLanguage] = useState(() => {
        try { return localStorage.getItem(storageKey) || defaultLanguage } catch { return defaultLanguage }
    })

    const t = useCallback((key) => {
        return resolveTranslation(language, key)
    }, [language])

    // Sync <html lang> attribute with current language (WCAG 3.1.1)
    useEffect(() => {
        document.documentElement.lang = language
    }, [language])

    const setLang = useCallback((lang) => {
        try { localStorage.setItem(storageKey, lang) } catch { /* quota exceeded or private browsing */ }
        setLanguage(lang)
    }, [storageKey])

    const value = useMemo(() => ({
        language,
        setLanguage: setLang,
        t,
    }), [language, setLang, t])

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
