"use client"

import { ChatPanel } from "@/components/chat-panel"
import { EventStream } from "@/components/event-stream"
import { Header } from "@/components/header"
import { useAgentStream } from "@/lib/use-agent-stream"

export default function Home() {
  const { items, events, thinking, running, send, clear } = useAgentStream()

  return (
    <div className="flex h-dvh flex-col">
      <Header />
      <main className="grid min-h-0 flex-1 grid-cols-1 grid-rows-2 md:grid-cols-2 md:grid-rows-1">
        <ChatPanel items={items} thinking={thinking} running={running} onSend={send} onClear={clear} />
        <EventStream events={events} />
      </main>
    </div>
  )
}
