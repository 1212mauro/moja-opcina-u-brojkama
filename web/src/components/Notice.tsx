import type { ReactNode } from "react";

import styles from "./Notice.module.css";

/** A section's "no data" state: says why, instead of leaving an empty gap (D12). */
export function Notice({ children }: { children: ReactNode }) {
  return (
    <p className={styles.notice} role="note">
      {children}
    </p>
  );
}
