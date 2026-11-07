import { CountyMap } from "@/components/CountyMap";
import { MunicipalitySearch } from "@/components/MunicipalitySearch";
import { loadSearchIndex } from "@/lib/data";
import type { Locale } from "@/lib/i18n";
import { getMessages } from "@/messages";
import styles from "./Home.module.css";

export function HomeView({ locale }: { locale: Locale }) {
  const msg = getMessages(locale);
  const { entries } = loadSearchIndex();
  const counties = [...new Set(entries.map((e) => e.county))];

  // H1: finding your town comes first. On desktop the map sits beside the search and
  // list; on phones it comes last, as the list is quicker to use on a small screen.
  return (
    <div className={styles.layout}>
      <div className={styles.primary}>
        <header className={styles.hero}>
          <h1>{msg.home.title}</h1>
          <p className={styles.lead}>{msg.home.intro}</p>
        </header>
        {/* One search across every county in scope. */}
        <MunicipalitySearch
          locale={locale}
          entries={entries}
          caption={
            counties.length === 1
              ? msg.home.tableCaption(counties[0])
              : msg.home.allUnits
          }
        />
      </div>
      <aside className={styles.aside}>
        <CountyMap locale={locale} title={msg.map.home} />
      </aside>
    </div>
  );
}
