import { Button } from '@/components/ui/button'
import { Camera } from 'lucide-react'

export default function CameraCaptureButton({ onCapture }) {
  return (
    <div className="border-t border-border pt-3">
      <Button
        variant="outline"
        size="sm"
        className="w-full gap-2 text-xs h-8"
        onClick={onCapture}
      >
        <Camera className="h-3 w-3" />
        Capture Camera Position
      </Button>
      <p className="text-[10px] text-muted-foreground mt-1">
        Orbit the 3D view first, then capture the current camera angle for this step.
      </p>
    </div>
  )
}
