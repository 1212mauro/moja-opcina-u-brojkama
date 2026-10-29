import { Notice } from "@/components/Notice";
import { SourceNote } from "@/components/SourceNote";
import type { Facility, MunicipalityPage } from "@/lib/contract";
import { hr } from "@/messages/hr";
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
export function FacilitiesSection({ page }: { page: MunicipalityPage }) {
  if (!page.facilities.length) return <Notice>{hr.missing.facilities}</Notice>;
  const runIds = [...new Set(page.facilities.map((f) => f.sourceRunId))];

  return (
    <>
      <p>{hr.facilities.intro(page.facilities.length)}</p>
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
                {hr.facilities.types[type]}{" "}
                <span className={styles.count}>({items.length})</span>
              </h3>
              <ul className={styles.list}>
                {items.map((facility, index) => (
                  <li key={`${index}-${facility.name}`}>
                    <span className={styles.name}>{facility.name}</span>
                    <span className={styles.address}>
                      {facility.address ?? hr.facilities.noAddress} ·{" "}
                      <a href={osmLink(facility)} rel="external">
                        {hr.facilities.mapLink}
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
      <SourceNote page={page} runIds={runIds} />
    </>
  );
}
