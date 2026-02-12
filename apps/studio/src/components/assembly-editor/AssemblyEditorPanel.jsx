import { useAssemblyEditor } from '../../hooks/useAssemblyEditor'
import { useLanguage } from '../../contexts/LanguageProvider'
import { useManifest } from '../../contexts/ManifestProvider'
import StepList from './StepList'
import StepDetailForm from './StepDetailForm'
import PartVisibilityPicker from './PartVisibilityPicker'
import CameraCaptureButton from './CameraCaptureButton'
import AssemblyEditorToolbar from './AssemblyEditorToolbar'

const ASSEMBLY_STEP_DELAY_MS = 2000

export default function AssemblyEditorPanel({ onStepChange, onClose, viewerRef, projectSlug }) {
  const { manifest } = useManifest()
  const { language } = useLanguage()

  const editor = useAssemblyEditor(manifest, projectSlug, onStepChange, viewerRef)
  const { steps, selectedIndex, selectedStep, isDirty, saving } = editor

  const allParts = manifest?.parts?.map(p => p.id) || []

  return (
    <div className="flex flex-col gap-3 h-full">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Assembly Editor</h2>
      </div>

      <StepList
        steps={steps}
        selectedIndex={selectedIndex}
        onSelect={editor.selectStep}
        onAdd={editor.addStep}
        onRemove={editor.removeStep}
        onReorder={editor.reorderStep}
        language={language}
      />

      {selectedStep && (
        <>
          <StepDetailForm
            step={selectedStep}
            index={selectedIndex}
            onUpdate={editor.updateStep}
            language={language}
          />

          <PartVisibilityPicker
            allParts={allParts}
            visibleParts={selectedStep.visible_parts || []}
            highlightParts={selectedStep.highlight_parts || []}
            onChange={(visible, highlight) => {
              editor.updateStep(selectedIndex, {
                visible_parts: visible,
                highlight_parts: highlight,
              })
              // Live-update viewer
              onStepChange?.({ ...selectedStep, visible_parts: visible, highlight_parts: highlight })
            }}
          />

          <CameraCaptureButton onCapture={editor.captureCamera} />
        </>
      )}

      <div className="flex-1" />

      <AssemblyEditorToolbar
        isDirty={isDirty}
        saving={saving}
        onSave={editor.save}
        onDiscard={editor.discard}
        onClose={onClose}
        onPreview={() => {
          // Play through steps sequentially
          let i = 0
          const play = () => {
            if (i >= steps.length) return
            editor.selectStep(i)
            i++
            if (i < steps.length) setTimeout(play, ASSEMBLY_STEP_DELAY_MS)
          }
          play()
        }}
      />
    </div>
  )
}
