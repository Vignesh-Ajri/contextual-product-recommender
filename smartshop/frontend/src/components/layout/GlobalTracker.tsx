"use client";

import { usePageViewTracker } from "@/hooks/useTracker";

export default function GlobalTracker() {
  usePageViewTracker();
  return null;
}
