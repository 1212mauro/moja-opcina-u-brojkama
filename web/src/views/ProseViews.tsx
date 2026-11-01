import type { Metadata } from "next";
import Link from "next/link";
import type { ComponentType } from "react";

import type { Locale } from "@/lib/i18n";
import { routePath } from "@/lib/paths";
import { getMessages } from "@/messages";
import { AccessibilityText as EnAccessibility } from "@/messages/en-accessibility";
import { MethodologyText as EnMethodology } from "@/messages/en-methodology";
import { AccessibilityText as HrAccessibility } from "@/messages/hr-accessibility";
import { MethodologyText as HrMethodology } from "@/messages/hr-methodology";
import { MethodologyText as SimpleMethodology } from "@/messages/hr-simple-methodology";
import styles from "./prose.module.css";

type Prose = ComponentType<{ leadClass: string }>;

const METHODOLOGY: Record<Locale, Prose> = {
  hr: HrMethodology,
  "hr-simple": SimpleMethodology,
  en: EnMethodology,
};

// The statement follows a legal template, so simple language keeps the standard text.
const ACCESSIBILITY: Record<Locale, Prose> = {
  hr: HrAccessibility,
  "hr-simple": HrAccessibility,
  en: EnAccessibility,
};

export function methodologyMetadata(locale: Locale): Metadata {
  return { title: getMessages(locale).site.nav.methodology };
}

/** D11: what the numbers are, where they come from, and what they do not say. */
export function MethodologyView({ locale }: { locale: Locale }) {
  const Text = METHODOLOGY[locale];
  return (
    <article className={styles.prose}>
      <Text leadClass={styles.lead} />
    </article>
  );
}

export function accessibilityMetadata(locale: Locale): Metadata {
  return { title: getMessages(locale).site.nav.accessibility };
}

/** E7: the accessibility statement. */
export function AccessibilityView({ locale }: { locale: Locale }) {
  const Text = ACCESSIBILITY[locale];
  return (
    <article className={styles.prose}>
      <Text leadClass={styles.lead} />
    </article>
  );
}

/** F2: the 404 page, in Croatian and English since the path says nothing about language. */
export function NotFoundView() {
  return (
    <article className={styles.prose}>
      {(["hr", "en"] as const).map((locale) => {
        const msg = getMessages(locale);
        return (
          <section key={locale} lang={locale === "en" ? "en" : undefined}>
            {locale === "hr" ? (
              <h1>{msg.notFound.title}</h1>
            ) : (
              <h2>{msg.notFound.title}</h2>
            )}
            <p className={styles.lead}>{msg.notFound.body}</p>
            <p>
              <Link href={routePath(locale, { page: "home" })}>
                {msg.notFound.home}
              </Link>
            </p>
          </section>
        );
      })}
    </article>
  );
}
