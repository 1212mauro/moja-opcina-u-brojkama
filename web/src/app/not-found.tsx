import type { Metadata } from "next";
import Link from "next/link";

import { hr } from "@/messages/hr";
import styles from "./prose.module.css";

export const metadata: Metadata = { title: hr.notFound.title };

/** F2: the static export writes this as 404.html, which GitHub Pages serves for unknown paths. */
export default function NotFound() {
  return (
    <article className={styles.prose}>
      <h1>{hr.notFound.title}</h1>
      <p className={styles.lead}>{hr.notFound.body}</p>
      <p>
        <Link href="/">{hr.notFound.home}</Link>
      </p>
    </article>
  );
}
