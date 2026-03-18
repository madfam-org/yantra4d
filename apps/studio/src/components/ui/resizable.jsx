import { GripVertical } from "lucide-react"
import { Group, Panel, Separator } from "react-resizable-panels"

import { cn } from "@/lib/utils"

const ResizablePanelGroup = ({
  className,
  orientation = "horizontal",
  ...props
}) => (
  <Group
    orientation={orientation}
    className={cn(
      "flex h-full w-full",
      orientation === "vertical" && "flex-col",
      className
    )}
    {...props}
  />
)

// v4 interprets numeric sizes as pixels; convert to percentage strings
// to preserve v2/v3 behavior where numbers meant percentages (0..100)
const toPercent = (v) => (typeof v === 'number' ? `${v}%` : v)

const ResizablePanel = ({ defaultSize, minSize, maxSize, collapsedSize, style, ...props }) => (
  <Panel
    defaultSize={toPercent(defaultSize)}
    minSize={toPercent(minSize)}
    maxSize={toPercent(maxSize)}
    collapsedSize={toPercent(collapsedSize)}
    style={{ height: '100%', ...style }}
    {...props}
  />
)

const ResizableHandle = ({
  withHandle,
  className,
  orientation,
  ...props
}) => (
  <Separator
    className={cn(
      "relative flex items-center justify-center bg-border focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-offset-1",
      orientation === "vertical"
        ? "h-px w-full after:absolute after:left-0 after:h-1 after:w-full after:-translate-y-1/2 after:translate-x-0"
        : "w-px after:absolute after:inset-y-0 after:left-1/2 after:w-1 after:-translate-x-1/2",
      className
    )}
    {...props}
  >
    {withHandle && (
      <div className={cn(
        "z-10 flex h-4 w-3 items-center justify-center rounded-sm border bg-border",
        orientation === "vertical" && "rotate-90"
      )}>
        <GripVertical className="h-2.5 w-2.5" />
      </div>
    )}
  </Separator>
)

export { ResizablePanelGroup, ResizablePanel, ResizableHandle }
