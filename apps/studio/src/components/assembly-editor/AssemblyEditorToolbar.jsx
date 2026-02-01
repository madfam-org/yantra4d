import { Button } from '@/components/ui/button'
import { Save, Undo2, Play, X } from 'lucide-react'

export default function AssemblyEditorToolbar({ isDirty, saving, onSave, onDiscard, onClose, onPreview }) {
  return (
    <div className="flex flex-col gap-1.5 border-t border-border pt-3">
      <div className="flex gap-1.5">
        <Button
          size="sm"
          className="flex-1 gap-1.5 text-xs h-8"
          onClick={onSave}
          disabled={!isDirty || saving}
        >
          <Save className="h-3 w-3" />
          {saving ? 'Saving...' : 'Save'}
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="flex-1 gap-1.5 text-xs h-8"
          onClick={onDiscard}
          disabled={!isDirty}
        >
          <Undo2 className="h-3 w-3" />
          Discard
        </Button>
      </div>
      <div className="flex gap-1.5">
        <Button
          variant="secondary"
          size="sm"
          className="flex-1 gap-1.5 text-xs h-8"
          onClick={onPreview}
        >
          <Play className="h-3 w-3" />
          Preview
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="flex-1 gap-1.5 text-xs h-8"
          onClick={onClose}
        >
          <X className="h-3 w-3" />
          Close
        </Button>
      </div>
    </div>
  )
}
