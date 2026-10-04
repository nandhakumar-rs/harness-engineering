"use client"

import { useCallback, useEffect, useRef, useState } from "react"

import type { ChatItem, HarnessEvent } from "./events"

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

/** Reads a fetch body as Server-Sent Events, yielding one parsed event per `data:` message. */
async function* readSSE(body: ReadableStream<Uint8Array>): AsyncGenerator<HarnessEvent> {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  while (true) {
    const { value, done } = await reader.read()
    if (done) return
    buffer += decoder.decode(value, { stream: true })
    let sep: number
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const chunk = buffer.slice(0, sep)
      buffer = buffer.slice(sep + 2)
      const data = chunk
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trimStart())
        .join("\n")
      if (data) yield JSON.parse(data) as HarnessEvent
    }
  }
}

/** Folds one harness event into the chat timeline. */
function applyEvent(items: ChatItem[], e: HarnessEvent): ChatItem[] {
  switch (e.type) {
    case "message.delta": {
      const last = items.at(-1)
      if (last?.kind === "assistant") {
        return [...items.slice(0, -1), { ...last, text: last.text + e.data.text }]
      }
      return [...items, { kind: "assistant", id: e.id, text: e.data.text }]
    }
    case "tool.requested":
      return [
        ...items,
        { kind: "tool", id: e.data.toolCallId, name: e.data.name, args: e.data.args, status: "running" },
      ]
    case "tool.completed":
    case "tool.failed":
      return items.map((item) =>
        item.kind === "tool" && item.id === e.data.toolCallId
          ? e.type === "tool.completed"
            ? { ...item, status: "completed", result: e.data.result }
            : { ...item, status: "failed", error: e.data.error }
          : item,
      )
    case "run.failed":
      return [...items, { kind: "error", id: e.id, text: e.data.error }]
    default:
      return items
  }
}

export function useAgentStream() {
  const [items, setItems] = useState<ChatItem[]>([])
  const [events, setEvents] = useState<HarnessEvent[]>([])
  const [thinking, setThinking] = useState(false)
  const [running, setRunning] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  const send = useCallback(
    async (text: string) => {
      const userItem: ChatItem = { kind: "user", id: crypto.randomUUID(), text }
      // Conversation history sent to the backend: user + assistant text only.
      const history = [...items, userItem].flatMap((item) =>
        item.kind === "user" || item.kind === "assistant"
          ? [{ role: item.kind, content: item.text }]
          : [],
      )
      setItems((prev) => [...prev, userItem])
      setRunning(true)

      const controller = new AbortController()
      abortRef.current = controller
      try {
        const res = await fetch(`${API_URL}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ messages: history }),
          signal: controller.signal,
        })
        if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`)
        for await (const e of readSSE(res.body)) {
          setEvents((prev) => [...prev, e])
          if (e.type === "thinking") setThinking(e.data.status === "started")
          setItems((prev) => applyEvent(prev, e))
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setItems((prev) => [
            ...prev,
            { kind: "error", id: crypto.randomUUID(), text: `Request failed: ${(err as Error).message}` },
          ])
        }
      } finally {
        setThinking(false)
        setRunning(false)
        abortRef.current = null
      }
    },
    [items],
  )

  const clear = useCallback(() => {
    abortRef.current?.abort()
    setItems([])
    setEvents([])
    setThinking(false)
    setRunning(false)
  }, [])

  return { items, events, thinking, running, send, clear }
}

/** Polls the backend health endpoint for the header's connection indicator. */
export function useBackendStatus(intervalMs = 5000) {
  const [connected, setConnected] = useState<boolean | null>(null)
  useEffect(() => {
    let cancelled = false
    const check = async () => {
      try {
        const res = await fetch(`${API_URL}/api/health`, { cache: "no-store" })
        if (!cancelled) setConnected(res.ok)
      } catch {
        if (!cancelled) setConnected(false)
      }
    }
    check()
    const id = setInterval(check, intervalMs)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [intervalMs])
  return connected
}
