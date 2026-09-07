"use client";

import { ReactNode, useCallback, useLayoutEffect, useRef, useState } from "react";

const VIEW_PAD = 8;
const GAP = 8;

type Place = "bottom" | "top";

/** Hover / focus tip; bubble stays inside the viewport. */
export function Tip({
  tip,
  children,
  placement = "bottom",
}: {
  tip: string;
  children: ReactNode;
  placement?: Place;
}) {
  const rootRef = useRef<HTMLSpanElement>(null);
  const bubbleRef = useRef<HTMLSpanElement>(null);
  const [open, setOpen] = useState(false);
  const [ready, setReady] = useState(false);
  const [coords, setCoords] = useState<{ left: number; top: number }>({ left: 0, top: 0 });

  const reposition = useCallback(() => {
    const root = rootRef.current;
    const bubble = bubbleRef.current;
    if (!root || !bubble) return;

    const tr = root.getBoundingClientRect();
    const br = bubble.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const bw = Math.min(br.width || bubble.offsetWidth, vw - VIEW_PAD * 2);
    const bh = br.height || bubble.offsetHeight;

    let place: Place = placement;
    const need = bh + GAP;
    const spaceBelow = vh - tr.bottom;
    const spaceAbove = tr.top;
    if (place === "bottom" && spaceBelow < need && spaceAbove > spaceBelow) place = "top";
    if (place === "top" && spaceAbove < need && spaceBelow > spaceAbove) place = "bottom";

    let top = place === "bottom" ? tr.bottom + GAP : tr.top - GAP - bh;
    let left = tr.left + tr.width / 2 - bw / 2;

    left = Math.min(Math.max(VIEW_PAD, left), vw - bw - VIEW_PAD);
    top = Math.min(Math.max(VIEW_PAD, top), vh - bh - VIEW_PAD);

    setCoords({ left, top });
  }, [placement]);

  useLayoutEffect(() => {
    if (!open) {
      setReady(false);
      return;
    }
    reposition();
    setReady(true);
    const onMove = () => reposition();
    window.addEventListener("scroll", onMove, true);
    window.addEventListener("resize", onMove);
    return () => {
      window.removeEventListener("scroll", onMove, true);
      window.removeEventListener("resize", onMove);
    };
  }, [open, tip, reposition]);

  return (
    <span
      ref={rootRef}
      className="topbar-tip relative inline-flex"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocusCapture={() => setOpen(true)}
      onBlurCapture={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setOpen(false);
      }}
    >
      {children}
      <span
        ref={bubbleRef}
        className={`topbar-tip__bubble${open && ready ? " topbar-tip__bubble--open" : ""}`}
        role="tooltip"
        aria-hidden={!open}
        style={{ left: coords.left, top: coords.top }}
      >
        {tip}
      </span>
    </span>
  );
}
