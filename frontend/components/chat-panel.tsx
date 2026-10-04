"use client"

import { ArrowUp, Eraser } from "lucide-react"
import { useState } from "react"

import { ThinkingIndicator } from "@/components/thinking-indicator"
import { ToolCallCard } from "@/components/tool-call-card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import type { ChatItem } from "@/lib/events"
import { useAutoscroll } from "@/lib/use-autoscroll"

type Props = {
  items: ChatItem[]
  thinking: boolean
  running: boolean
  onSend: (text: string) => void
  onClear: () => void
}

export function ChatPanel({ items, thinking, running, onSend, onClear }: Props) {
  const [input, setInput] = useState("")
  const scrollRef = useAutoscroll<HTMLDivElement>([items, thinking])

  const submit = () => {
    const text = input.trim()
    if (!text || running) return
    onSend(text)
    setInput("")
  }

  return (
    <section className="flex min-h-0 flex-col">
      <div className="flex h-14 shrink-0 items-center justify-between border-b px-5">
        <h2 className="font-medium">Agent</h2>
        <Button variant="ghost" size="sm" onClick={onClear} className="text-muted-foreground">
          <Eraser /> Clear
        </Button>
      </div>

      <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
        {items.length === 0 && !thinking ? (
          <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">
            Paste a customer ticket or give the agent an objective.
          </div>
        ) : (
          <div className="space-y-3">
            {items.map((item) => (
              <ChatRow key={item.id} item={item} />
            ))}
            {thinking && <ThinkingIndicator />}
          </div>
        )}
      </div>

      <div className="shrink-0 p-4">
        <div className="rounded-2xl border bg-card/40 p-2 focus-within:ring-2 focus-within:ring-ring/40">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                submit()
              }
            }}
            placeholder="Give the agent an objective..."
            className="max-h-48 min-h-14 resize-none border-0 bg-transparent shadow-none focus-visible:ring-0 dark:bg-transparent"
          />
          <div className="flex justify-end">
            <Button size="icon" className="rounded-full" onClick={submit} disabled={!input.trim() || running} aria-label="Send">
              <ArrowUp />
            </Button>
          </div>
        </div>
      </div>
    </section>
  )
}

function ChatRow({ item }: { item: ChatItem }) {
  switch (item.kind) {
    case "user":
      return (
        <div className="flex justify-end">
          <div className="max-w-[85%] rounded-2xl bg-secondary px-4 py-2.5 text-sm whitespace-pre-wrap">{item.text}</div>
        </div>
      )
    case "assistant":
      return <div className="px-1 text-sm leading-relaxed whitespace-pre-wrap">{item.text}</div>
    case "tool":
      return <ToolCallCard tool={item} />
    case "error":
      return (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2.5 font-mono text-xs text-red-500">
          {item.text}
        </div>
      )
  }
}
