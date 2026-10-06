"use client"

import { useCallback, useEffect, useRef, useState } from "react"

import type { ChatItem, HarnessEvent } from "./events"

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

const LAST_RUN_KEY = "harness.lastRunId"
const TERMINAL = new Set(["run.completed", "run.failed"])

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
    case "run.started": {
      // Rebuilding after a refresh: the user's message comes back from the log.
      const id = `user-${e.data.runId}`
      if (!e.data.input || items.some((item) => item.id === id)) return items
      return [...items, { kind: "user", id, text: e.data.input }]
    }
    case "message.delta": {
      const last = items.at(-1)
      if (last?.kind === "assistant") {
        if (last.completed) return items // late live words for a message we already have in full
        return [...items.slice(0, -1), { ...last, text: last.text + e.data.text }]
      }
      return [...items, { kind: "assistant", id: e.id, text: e.data.text }]
    }
    case "message.completed": {
      // The stored full text replaces whatever words arrived live (or arrives alone on catch-up).
      const last = items.at(-1)
      if (last?.kind === "assistant" && !last.completed) {
        return [...items.slice(0, -1), { ...last, text: e.data.text, completed: true }]
      }
      return [...items, { kind: "assistant", id: e.id, text: e.data.text, completed: true }]
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

function newRunId() {
  return crypto.randomUUID().replaceAll("-", "").slice(0, 12)
}

function saveLastRun(runId: string | null) {
  try {
    if (runId) localStorage.setItem(LAST_RUN_KEY, runId)
    else localStorage.removeItem(LAST_RUN_KEY)
  } catch {}
}

function loadLastRun(): string | null {
  try {
    return localStorage.getItem(LAST_RUN_KEY)
  } catch {
    return null
  }
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

export function useAgentStream() {
  const [items, setItems] = useState<ChatItem[]>([])
  const [events, setEvents] = useState<HarnessEvent[]>([])
  const [thinking, setThinking] = useState(false)
  const [running, setRunning] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  /**
   * Follow a run until it ends: GET /api/runs/{id}/events?after=<last seq seen>.
   * If the connection drops (server restart, network), reconnect from where we were.
   */
  const watch = useCallback(async (runId: string, controller: AbortController) => {
    let lastSeq = 0
    let finished = false
    setRunning(true)
    while (!finished && !controller.signal.aborted) {
      try {
        const res = await fetch(`${API_URL}/api/runs/${runId}/events?after=${lastSeq}`, {
          signal: controller.signal,
        })
        if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`)
        for await (const e of readSSE(res.body)) {
          if (e.seq != null) {
            if (e.seq <= lastSeq) continue
            lastSeq = e.seq
          }
          setEvents((prev) => [...prev, e])
          if (e.type === "thinking") setThinking(e.data.status === "started")
          if (e.type === "message.delta") setThinking(false) // words are arriving: the model is no longer thinking
          setItems((prev) => applyEvent(prev, e))
          if (TERMINAL.has(e.type)) finished = true
        }
      } catch {
        // dropped or refused: fall through and retry
      }
      if (!finished && !controller.signal.aborted) await sleep(1000)
    }
    if (!controller.signal.aborted) {
      setThinking(false)
      setRunning(false)
    }
  }, [])

  // After a refresh, rebuild the last run from the log (and keep following it if it's still going).
  useEffect(() => {
    const runId = loadLastRun()
    if (!runId) return
    const controller = new AbortController()
    abortRef.current = controller
    void watch(runId, controller)
    return () => controller.abort()
  }, [watch])

  const send = useCallback(
    async (text: string) => {
      const runId = newRunId()
      const userItem: ChatItem = { kind: "user", id: `user-${runId}`, text }
      // Conversation history sent to the backend: user + assistant text only.
      const history = [...items, userItem].flatMap((item) =>
        item.kind === "user" || item.kind === "assistant"
          ? [{ role: item.kind, content: item.text }]
          : [],
      )
      setItems((prev) => [...prev, userItem])
      saveLastRun(runId)

      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller
      try {
        const res = await fetch(`${API_URL}/api/runs`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ runId, messages: history }),
          signal: controller.signal,
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
      } catch (err) {
        if (!controller.signal.aborted) {
          setItems((prev) => [
            ...prev,
            { kind: "error", id: crypto.randomUUID(), text: `Could not start the run: ${(err as Error).message}` },
          ])
        }
        return
      }
      await watch(runId, controller)
    },
    [items, watch],
  )

  const clear = useCallback(() => {
    abortRef.current?.abort() // stops watching; the run itself keeps going on the server
    saveLastRun(null)
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
