import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'

export default function StepDetailForm({ step, index, onUpdate, language }) {
  const handleLabelChange = (lang, value) => {
    const newLabel = { ...(step.label || {}), [lang]: value }
    onUpdate(index, { label: newLabel })
  }

  const handleNotesChange = (lang, value) => {
    const newNotes = { ...(step.notes || {}), [lang]: value }
    onUpdate(index, { notes: newNotes })
  }

  return (
    <div className="flex flex-col gap-2 border-t border-border pt-3">
      <div className="space-y-1">
        <Label className="text-xs">Label ({language.toUpperCase()})</Label>
        <Input
          value={(step.label && step.label[language]) || ''}
          onChange={(e) => handleLabelChange(language, e.target.value)}
          placeholder="Step title..."
          className="h-8 text-xs"
        />
      </div>

      <div className="space-y-1">
        <Label className="text-xs">Notes ({language.toUpperCase()})</Label>
        <Textarea
          value={(step.notes && step.notes[language]) || ''}
          onChange={(e) => handleNotesChange(language, e.target.value)}
          placeholder="Instructions, tips..."
          className="text-xs min-h-[60px] resize-none"
          rows={2}
        />
      </div>
    </div>
  )
}
