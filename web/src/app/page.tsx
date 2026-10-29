import { MunicipalitySearch } from "@/components/MunicipalitySearch";
import { loadSearchIndex } from "@/lib/data";
import { hr } from "@/messages/hr";
import styles from "./page.module.css";

export default function Home() {
  const { entries } = loadSearchIndex();
  const counties = [...new Set(entries.map((e) => e.county))];

  return (
    <>
      <header className={styles.hero}>
        <h1>{hr.home.title}</h1>
        <p className={styles.lead}>{hr.home.intro}</p>
      </header>
      {/* One search across every county in scope. */}
      <MunicipalitySearch
        entries={entries}
        caption={
          counties.length === 1
            ? hr.home.tableCaption(counties[0])
            : hr.home.allUnits
        }
      />
    </>
  );
}
