import React from 'react'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'

interface Step {
  label?: Record<string, string>
  notes?: Record<string, string>
  [key: string]: unknown
}

interface StepDetailFormProps {
  step: Step
  index: number
  onUpdate: (index: number, changes: Partial<Step>) => void
  language: string
}

export default function StepDetailForm({ step, index, onUpdate, language }: StepDetailFormProps) {
  const handleLabelChange = (lang: string, value: string) => {
    const newLabel = { ...(step.label || {}), [lang]: value }
    onUpdate(index, { label: newLabel })
  }

  const handleNotesChange = (lang: string, value: string) => {
    const newNotes = { ...(step.notes || {}), [lang]: value }
    onUpdate(index, { notes: newNotes })
  }

  return (
    <div className="flex flex-col gap-2 border-t border-border pt-3">
      <div className="space-y-1">
        <Label className="text-xs">Label ({language.toUpperCase()})</Label>
        <Input
          value={(step.label && step.label[language]) || ''}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleLabelChange(language, e.target.value)}
          placeholder="Step title..."
          className="h-8 text-xs"
        />
      </div>

      <div className="space-y-1">
        <Label className="text-xs">Notes ({language.toUpperCase()})</Label>
        <Textarea
          value={(step.notes && step.notes[language]) || ''}
          onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => handleNotesChange(language, e.target.value)}
          placeholder="Instructions, tips..."
          className="text-xs min-h-[60px] resize-none"
          rows={2}
        />
      </div>
    </div>
  )
}
