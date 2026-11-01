import type { Locale } from "@/lib/i18n";
import { en } from "@/messages/en";
import { hr, type Messages } from "@/messages/hr";
import { hrSimple } from "@/messages/hr-simple";

export type { Messages };

const MESSAGES: Record<Locale, Messages> = {
  hr,
  "hr-simple": hrSimple,
  en,
};

export function getMessages(locale: Locale): Messages {
  return MESSAGES[locale];
}
