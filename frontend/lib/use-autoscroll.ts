"use client"

import { useEffect, useRef } from "react"

/** Keeps a scroll container pinned to the bottom while `dep` changes, unless the user scrolled up. */
export function useAutoscroll<T extends HTMLElement>(dep: unknown) {
  const ref = useRef<T>(null)
  const pinned = useRef(true)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    let lastTop = el.scrollTop
    const onScroll = () => {
      const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40
      // Only an upward scroll unpins; our own scroll-to-bottom never moves up.
      if (el.scrollTop < lastTop && !atBottom) pinned.current = false
      else if (atBottom) pinned.current = true
      lastTop = el.scrollTop
    }
    el.addEventListener("scroll", onScroll)
    return () => el.removeEventListener("scroll", onScroll)
  }, [])

  useEffect(() => {
    const el = ref.current
    if (el && pinned.current) el.scrollTop = el.scrollHeight
  }, [dep])

  return ref
}
