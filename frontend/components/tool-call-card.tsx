"use client"

import { ChevronDown, CircleCheck, CircleX, Loader2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import type { ChatItem } from "@/lib/events"
import { cn } from "@/lib/utils"

type ToolItem = Extract<ChatItem, { kind: "tool" }>

const STATUS = {
  running: { label: "Running", icon: Loader2, className: "text-amber-500", badge: "bg-amber-500/15 text-amber-500" },
  completed: { label: "Completed", icon: CircleCheck, className: "text-emerald-500", badge: "bg-emerald-500/15 text-emerald-500" },
  failed: { label: "Failed", icon: CircleX, className: "text-red-500", badge: "bg-red-500/15 text-red-500" },
} as const

export function ToolCallCard({ tool }: { tool: ToolItem }) {
  const s = STATUS[tool.status]
  const Icon = s.icon

  return (
    <Collapsible className="rounded-xl border bg-card/50 transition-colors hover:bg-card">
      <CollapsibleTrigger className="group flex w-full items-center gap-3 px-4 py-3 text-left">
        <Icon className={cn("size-5 shrink-0", s.className, tool.status === "running" && "animate-spin")} />
        <span className="font-mono text-[15px] font-medium">{tool.name}</span>
        <Badge className={cn("border-0", s.badge)}>{s.label}</Badge>
        <ChevronDown className="ml-auto size-4 text-muted-foreground transition-transform group-data-[panel-open]:rotate-180" />
      </CollapsibleTrigger>
      <CollapsibleContent className="space-y-3 border-t px-4 py-3">
        <JsonBlock label="Arguments" value={tool.args} />
        {tool.status === "completed" && <JsonBlock label="Result" value={tool.result} />}
        {tool.status === "failed" && <JsonBlock label="Error" value={tool.error} />}
      </CollapsibleContent>
    </Collapsible>
  )
}

function JsonBlock({ label, value }: { label: string; value: unknown }) {
  return (
    <div>
      <div className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</div>
      <pre className="overflow-x-auto rounded-lg bg-muted/60 p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap break-all">
        {JSON.stringify(value, null, 2)}
      </pre>
    </div>
  )
}
