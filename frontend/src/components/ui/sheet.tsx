// shadcn/ui Sheet pattern using Radix Dialog: focus trap, Escape and focus return.
import type { ComponentProps, ReactNode } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { X } from 'lucide-react'

export function Sheet(props: ComponentProps<typeof Dialog.Root>) { return <Dialog.Root {...props} /> }
export function SheetTrigger(props: ComponentProps<typeof Dialog.Trigger>) { return <Dialog.Trigger {...props} /> }
export function SheetContent({ children }: { children: ReactNode }) {
  return <Dialog.Portal>
    <Dialog.Overlay className="sheet-overlay" />
    <Dialog.Content className="sheet-content" aria-describedby="mobile-navigation-description">
      <Dialog.Title className="sr-only">Navegación principal</Dialog.Title>
      <Dialog.Description id="mobile-navigation-description" className="sr-only">
        Selecciona una sección de EpiSentinel AI. Pulsa Escape para cerrar.
      </Dialog.Description>
      {children}
      <Dialog.Close className="sheet-close button button-icon button-ghost" aria-label="Cerrar menú"><X aria-hidden="true" size={20} /></Dialog.Close>
    </Dialog.Content>
  </Dialog.Portal>
}
