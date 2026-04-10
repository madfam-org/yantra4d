/* eslint-disable @typescript-eslint/no-explicit-any */

// Ambient declarations for shadcn/ui components (JSX, not migrated to TS).
// These are managed by the shadcn CLI and must not be hand-edited.
// Using permissive types so TSX consumers compile without errors.

declare module '@/components/ui/button' {
  import * as React from 'react'
  export const Button: React.ForwardRefExoticComponent<any>
  export function buttonVariants(props?: any): string
}

declare module '@/components/ui/sheet' {
  import * as React from 'react'
  export const Sheet: React.FC<any>
  export const SheetTrigger: React.ForwardRefExoticComponent<any>
  export const SheetClose: React.ForwardRefExoticComponent<any>
  export const SheetContent: React.ForwardRefExoticComponent<any>
  export const SheetHeader: React.FC<any>
  export const SheetFooter: React.FC<any>
  export const SheetTitle: React.ForwardRefExoticComponent<any>
  export const SheetDescription: React.ForwardRefExoticComponent<any>
}

declare module '@/components/ui/resizable' {
  import * as React from 'react'
  export const ResizablePanelGroup: React.FC<any>
  export const ResizablePanel: React.FC<any>
  export const ResizableHandle: React.FC<any>
}

declare module '@/components/ui/sonner' {
  import * as React from 'react'
  export const Toaster: React.FC<any>
}

declare module '@/components/ui/accordion' {
  import * as React from 'react'
  export const Accordion: React.ForwardRefExoticComponent<any>
  export const AccordionItem: React.ForwardRefExoticComponent<any>
  export const AccordionTrigger: React.ForwardRefExoticComponent<any>
  export const AccordionContent: React.ForwardRefExoticComponent<any>
}

declare module '@/components/ui/alert-dialog' {
  import * as React from 'react'
  export const AlertDialog: React.FC<any>
  export const AlertDialogTrigger: React.ForwardRefExoticComponent<any>
  export const AlertDialogContent: React.ForwardRefExoticComponent<any>
  export const AlertDialogHeader: React.FC<any>
  export const AlertDialogFooter: React.FC<any>
  export const AlertDialogTitle: React.ForwardRefExoticComponent<any>
  export const AlertDialogDescription: React.ForwardRefExoticComponent<any>
  export const AlertDialogAction: React.ForwardRefExoticComponent<any>
  export const AlertDialogCancel: React.ForwardRefExoticComponent<any>
}

declare module '@/components/ui/badge' {
  import * as React from 'react'
  export const Badge: React.ForwardRefExoticComponent<any>
  export function badgeVariants(props?: any): string
}

declare module '@/components/ui/card' {
  import * as React from 'react'
  export const Card: React.ForwardRefExoticComponent<any>
  export const CardHeader: React.ForwardRefExoticComponent<any>
  export const CardTitle: React.ForwardRefExoticComponent<any>
  export const CardDescription: React.ForwardRefExoticComponent<any>
  export const CardContent: React.ForwardRefExoticComponent<any>
  export const CardFooter: React.ForwardRefExoticComponent<any>
}

declare module '@/components/ui/checkbox' {
  import * as React from 'react'
  export const Checkbox: React.ForwardRefExoticComponent<any>
}

declare module '@/components/ui/dropdown-menu' {
  import * as React from 'react'
  export const DropdownMenu: React.FC<any>
  export const DropdownMenuTrigger: React.ForwardRefExoticComponent<any>
  export const DropdownMenuContent: React.ForwardRefExoticComponent<any>
  export const DropdownMenuItem: React.ForwardRefExoticComponent<any>
  export const DropdownMenuSeparator: React.ForwardRefExoticComponent<any>
  export const DropdownMenuLabel: React.ForwardRefExoticComponent<any>
  export const DropdownMenuGroup: React.ForwardRefExoticComponent<any>
  export const DropdownMenuSub: React.FC<any>
  export const DropdownMenuSubTrigger: React.ForwardRefExoticComponent<any>
  export const DropdownMenuSubContent: React.ForwardRefExoticComponent<any>
  export const DropdownMenuRadioGroup: React.FC<any>
  export const DropdownMenuRadioItem: React.ForwardRefExoticComponent<any>
}

declare module '@/components/ui/input' {
  import * as React from 'react'
  export const Input: React.ForwardRefExoticComponent<any>
}

declare module '@/components/ui/label' {
  import * as React from 'react'
  export const Label: React.ForwardRefExoticComponent<any>
}

declare module '@/components/ui/select' {
  import * as React from 'react'
  export const Select: React.FC<any>
  export const SelectTrigger: React.ForwardRefExoticComponent<any>
  export const SelectValue: React.ForwardRefExoticComponent<any>
  export const SelectContent: React.ForwardRefExoticComponent<any>
  export const SelectItem: React.ForwardRefExoticComponent<any>
  export const SelectGroup: React.ForwardRefExoticComponent<any>
}

declare module '@/components/ui/slider' {
  import * as React from 'react'
  export const Slider: React.ForwardRefExoticComponent<any>
}

declare module '@/components/ui/switch' {
  import * as React from 'react'
  export const Switch: React.ForwardRefExoticComponent<any>
}

declare module '@/components/ui/table' {
  import * as React from 'react'
  export const Table: React.ForwardRefExoticComponent<any>
  export const TableHeader: React.ForwardRefExoticComponent<any>
  export const TableBody: React.ForwardRefExoticComponent<any>
  export const TableRow: React.ForwardRefExoticComponent<any>
  export const TableHead: React.ForwardRefExoticComponent<any>
  export const TableCell: React.ForwardRefExoticComponent<any>
}

declare module '@/components/ui/tabs' {
  import * as React from 'react'
  export const Tabs: React.FC<any>
  export const TabsList: React.ForwardRefExoticComponent<any>
  export const TabsTrigger: React.ForwardRefExoticComponent<any>
  export const TabsContent: React.ForwardRefExoticComponent<any>
}

declare module '@/components/ui/textarea' {
  import * as React from 'react'
  export const Textarea: React.ForwardRefExoticComponent<any>
}

declare module '@/components/ui/toggle' {
  import * as React from 'react'
  export const Toggle: React.ForwardRefExoticComponent<any>
}

declare module '@/components/ui/toggle-group' {
  import * as React from 'react'
  export const ToggleGroup: React.ForwardRefExoticComponent<any>
  export const ToggleGroupItem: React.ForwardRefExoticComponent<any>
}

declare module '@/components/ui/tooltip' {
  import * as React from 'react'
  export const Tooltip: React.FC<any>
  export const TooltipTrigger: React.ForwardRefExoticComponent<any>
  export const TooltipContent: React.ForwardRefExoticComponent<any>
  export const TooltipProvider: React.FC<any>
}
