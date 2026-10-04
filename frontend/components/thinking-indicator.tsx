import { Loader2 } from "lucide-react"

export function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-2 px-1 text-sm text-muted-foreground">
      <Loader2 className="size-4 animate-spin" />
      <span className="animate-pulse">Thinking…</span>
    </div>
  )
}
