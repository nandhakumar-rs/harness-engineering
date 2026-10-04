// Mirror of backend/app/events.py — every event is { id, ts, type, data }.

export type HarnessEvent =
  | E<"run.started", { runId: string }>
  | E<"run.completed", { runId: string; iterations?: number }>
  | E<"run.failed", { runId?: string; error: string }>
  | E<"iteration.started", { iteration: number; max: number }>
  | E<"thinking", { status: "started" | "stopped" }>
  | E<"message.delta", { text: string }>
  | E<"tool.requested", { toolCallId: string; name: string; args: unknown }>
  | E<"tool.completed", { toolCallId: string; result: unknown }>
  | E<"tool.failed", { toolCallId: string; error: string }>

type E<T extends string, D> = { id: string; ts: number; type: T; data: D }

export type HarnessEventType = HarnessEvent["type"]

export type ToolStatus = "running" | "completed" | "failed"

export type ChatItem =
  | { kind: "user"; id: string; text: string }
  | { kind: "assistant"; id: string; text: string }
  | {
      kind: "tool"
      id: string
      name: string
      args: unknown
      status: ToolStatus
      result?: unknown
      error?: string
    }
  | { kind: "error"; id: string; text: string }
