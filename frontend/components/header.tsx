"use client"

import { Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"

import { Button } from "@/components/ui/button"
import { useBackendStatus } from "@/lib/use-agent-stream"
import { cn } from "@/lib/utils"

export function Header() {
  const connected = useBackendStatus()
  const { resolvedTheme, setTheme } = useTheme()

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b px-5">
      <h1 className="text-base font-semibold tracking-tight">
        Harness <span className="font-normal text-muted-foreground">Inspector</span>
      </h1>
      <div className="flex items-center gap-4">
        <span
          className={cn(
            "flex items-center gap-2 text-sm",
            connected ? "text-emerald-500" : connected === false ? "text-red-500" : "text-muted-foreground",
          )}
        >
          <span
            className={cn(
              "size-2 rounded-full",
              connected ? "bg-emerald-500" : connected === false ? "bg-red-500" : "bg-muted-foreground",
            )}
          />
          {connected ? "connected" : connected === false ? "disconnected" : "connecting"}
        </span>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="Toggle theme"
          onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
        >
          <Sun className="hidden dark:block" />
          <Moon className="dark:hidden" />
        </Button>
      </div>
    </header>
  )
}
