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
      {counties.map((county) => (
        <MunicipalitySearch
          key={county}
          caption={hr.home.tableCaption(county)}
          entries={entries.filter((e) => e.county === county)}
        />
      ))}
    </>
  );
}
