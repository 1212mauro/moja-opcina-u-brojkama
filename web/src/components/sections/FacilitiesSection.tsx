import { Notice } from "@/components/Notice";
import { SourceNote } from "@/components/SourceNote";
import type { Facility, MunicipalityPage } from "@/lib/contract";
import type { Locale } from "@/lib/i18n";
import { getMessages } from "@/messages";
import styles from "./FacilitiesSection.module.css";

const ORDER: Facility["type"][] = ["school", "kindergarten", "health"];

function osmLink(facility: Facility): string {
  const { lat, lon } = facility;
  return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=17/${lat}/${lon}`;
}

/**
 * Facilities as a text list grouped by type (D9). The list is the content; a map is
 * an optional extra (SPEC: "the map is optional, the list is not").
 */
export function FacilitiesSection({
  locale,
  page,
}: {
  locale: Locale;
  page: MunicipalityPage;
}) {
  const msg = getMessages(locale);
  if (!page.facilities.length) return <Notice>{msg.missing.facilities}</Notice>;
  const runIds = [...new Set(page.facilities.map((f) => f.sourceRunId))];

  return (
    <>
      <p>{msg.facilities.intro(page.facilities.length)}</p>
      <div className={styles.groups}>
        {ORDER.map((type) => {
          const items = page.facilities.filter((f) => f.type === type);
          if (!items.length) return null;
          return (
            <section
              key={type}
              className={styles.group}
              aria-labelledby={`ustanove-${type}`}
            >
              <h3 id={`ustanove-${type}`}>
                {msg.facilities.types[type]}{" "}
                <span className={styles.count}>({items.length})</span>
              </h3>
              <ul className={styles.list}>
                {items.map((facility, index) => (
                  <li key={`${index}-${facility.name}`}>
                    <span className={styles.name}>{facility.name}</span>
                    <span className={styles.address}>
                      {facility.address ?? msg.facilities.noAddress} ·{" "}
                      <a href={osmLink(facility)} rel="external">
                        {msg.facilities.mapLink}
                        <span className="visually-hidden">
                          : {facility.name}
                        </span>
                      </a>
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          );
        })}
      </div>
      <SourceNote locale={locale} page={page} runIds={runIds} />
    </>
  );
}
