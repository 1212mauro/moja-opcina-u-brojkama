import type { Metadata } from "next";

import { hr } from "@/messages/hr";
import { MethodologyText } from "@/messages/hr-methodology";
import styles from "../prose.module.css";

export const metadata: Metadata = { title: hr.site.nav.methodology };

/** D11: what the numbers are, where they come from, and what they do not say. */
export default function Methodology() {
  return (
    <article className={styles.prose}>
      <MethodologyText leadClass={styles.lead} />
    </article>
  );
}
