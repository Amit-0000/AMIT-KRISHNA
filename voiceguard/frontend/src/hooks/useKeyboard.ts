import { useEffect } from 'react'

type ModKey = 'meta' | 'ctrl' | 'shift' | 'alt'

interface ShortcutOptions {
  key: string
  mods?: ModKey[]
  onPress: () => void
  enabled?: boolean
}

export function useKeyboard(shortcuts: ShortcutOptions[]) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      for (const shortcut of shortcuts) {
        if (shortcut.enabled === false) continue
        const keyMatch = e.key.toLowerCase() === shortcut.key.toLowerCase()
        if (!keyMatch) continue

        const mods = shortcut.mods ?? []
        const metaMatch = !mods.includes('meta') || e.metaKey
        const ctrlMatch = !mods.includes('ctrl') || e.ctrlKey
        const shiftMatch = !mods.includes('shift') || e.shiftKey
        const altMatch = !mods.includes('alt') || e.altKey

        // Require at least one of meta/ctrl when specified
        const needsMetaOrCtrl = mods.includes('meta') || mods.includes('ctrl')
        const hasMetaOrCtrl = e.metaKey || e.ctrlKey
        if (needsMetaOrCtrl && !hasMetaOrCtrl) continue

        if (metaMatch && ctrlMatch && shiftMatch && altMatch) {
          e.preventDefault()
          shortcut.onPress()
          return
        }
      }
    }

    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [shortcuts])
}
