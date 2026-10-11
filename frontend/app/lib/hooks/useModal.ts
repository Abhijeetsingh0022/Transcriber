"use client";

import { useState, useCallback } from "react";

type ModalVariant = "danger" | "warning" | "info";

type ModalState =
  | { type: "confirm"; title: string; message: string; variant?: ModalVariant; onConfirm: () => void }
  | { type: "alert";   title: string; message: string; variant?: ModalVariant }
  | null;

export function useModal() {
  const [modal, setModal] = useState<ModalState>(null);

  const confirm = useCallback(
    (title: string, message: string, onConfirm: () => void, variant: ModalVariant = "danger") =>
      setModal({ type: "confirm", title, message, variant, onConfirm }),
    []
  );

  const alert = useCallback(
    (title: string, message: string, variant: ModalVariant = "warning") =>
      setModal({ type: "alert", title, message, variant }),
    []
  );

  const close = useCallback(() => setModal(null), []);

  return { modal, confirm, alert, close };
}
