"use client";

import { useCallback, useEffect, useState } from "react";
import { createShuffleSeed, shuffleWithSeed } from "./random-order";

export function useListShuffle(listKey = "") {
  const [seed, setSeed] = useState("");
  const reshuffle = useCallback(() => setSeed(createShuffleSeed()), []);

  // Keep server output and hydration identical, then randomize each opened list.
  useEffect(reshuffle, [listKey, reshuffle]);

  const shuffle = useCallback(<T,>(items: readonly T[], salt = "") => (
    shuffleWithSeed(items, seed ? `${seed}:${salt}` : "")
  ), [seed]);

  return { shuffle, reshuffle };
}
