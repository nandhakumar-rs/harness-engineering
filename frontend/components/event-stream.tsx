"use client"

import type { HarnessEvent, HarnessEventType } from "@/lib/events"
import { useAutoscroll } from "@/lib/use-autoscroll"
import { cn } from "@/lib/utils"

const TYPE_COLOR: Record<HarnessEventType, string> = {
  "run.started": "text-sky-500",
  "run.completed": "text-sky-500",
  "run.failed": "text-red-500",
  "iteration.started": "text-violet-500",
  thinking: "text-muted-foreground",
  "message.delta": "text-zinc-400",
  "message.completed": "text-zinc-300",
  "tool.requested": "text-amber-500",
  "tool.completed": "text-emerald-500",
  "tool.failed": "text-red-500",
}

type Row = { id: string; ts: number; type: HarnessEventType; label: string; body: string }

/** One row per event, except consecutive message.delta events collapse into a single row. */
function toRows(events: HarnessEvent[]): Row[] {
  const rows: Row[] = []
  let deltas: { first: HarnessEvent; text: string; count: number } | null = null
  const flush = () => {
    if (!deltas) return
    rows.push({
      id: deltas.first.id,
      ts: deltas.first.ts,
      type: "message.delta",
      label: deltas.count > 1 ? `message.delta ×${deltas.count}` : "message.delta",
      body: JSON.stringify({ text: deltas.text }),
    })
    deltas = null
  }
  for (const e of events) {
    if (e.type === "message.delta") {
      if (deltas) {
        deltas.text += e.data.text
        deltas.count++
      } else deltas = { first: e, text: e.data.text, count: 1 }
      continue
    }
    flush()
    rows.push({ id: e.id, ts: e.ts, type: e.type, label: e.type, body: JSON.stringify(e.data) })
  }
  flush()
  return rows
}

function formatTime(ts: number) {
  return new Date(ts).toLocaleTimeString("en-GB", { hour12: false })
}

export function EventStream({ events }: { events: HarnessEvent[] }) {
  const scrollRef = useAutoscroll<HTMLDivElement>(events.length)
  const rows = toRows(events)

  return (
    <section className="flex min-h-0 flex-col border-t md:border-t-0 md:border-l">
      <div className="flex h-14 shrink-0 items-center justify-between border-b px-5">
        <h2 className="font-medium">Event stream</h2>
        <span className="text-sm text-muted-foreground tabular-nums">
          {events.length} {events.length === 1 ? "event" : "events"}
        </span>
      </div>

      <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto px-5 py-3 font-mono text-xs leading-5">
        {rows.length === 0 ? (
          <div className="flex h-full items-center justify-center font-sans text-sm text-muted-foreground">
            Events from the harness will appear here.
          </div>
        ) : (
          rows.map((row) => (
            <div key={row.id} className="grid grid-cols-[auto_10rem_1fr] gap-3 py-1">
              <span className="text-muted-foreground tabular-nums">{formatTime(row.ts)}</span>
              <span className={cn("truncate", TYPE_COLOR[row.type])}>{row.label}</span>
              <span className="break-all whitespace-pre-wrap text-foreground/80">{row.body}</span>
            </div>
          ))
        )}
      </div>
    </section>
  )
}
