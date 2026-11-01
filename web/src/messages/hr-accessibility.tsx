import { getFormat } from "@/lib/format";
import {
  ACCESSIBILITY_STATEMENT_DATE,
  contactEmail,
  SITE_URL,
} from "@/lib/site";

/**
 * Izjava o pristupačnosti (E7), po predlošku iz Provedbene odluke Komisije (EU)
 * 2018/1523, kako ga traži Zakon o pristupačnosti (NN 17/19).
 */
export function AccessibilityText({ leadClass }: { leadClass: string }) {
  const date = getFormat("hr").date(ACCESSIBILITY_STATEMENT_DATE);
  const email = contactEmail();
  return (
    <>
      <h1>Izjava o pristupačnosti</h1>
      <p className={leadClass}>
        Projekt „Moja općina u brojkama” nastoji svoju mrežnu stranicu učiniti
        pristupačnom, u skladu sa Zakonom o pristupačnosti mrežnih stranica i
        programskih rješenja za pokretne uređaje tijela javnog sektora (NN
        17/19).
      </p>
      <p>
        Ova izjava o pristupačnosti odnosi se na mrežnu stranicu{" "}
        <a href={SITE_URL}>{SITE_URL}</a>.
      </p>

      <h2>Stupanj usklađenosti</h2>
      <p>
        Ova mrežna stranica <strong>djelomično je usklađena</strong> sa Zakonom
        i normom EN 301 549 (WCAG 2.1, razina AA) zbog neusklađenosti navedenih
        u nastavku.
      </p>

      <h2>Nepristupačni sadržaj</h2>
      <h3>Neusklađenost sa Zakonom</h3>
      <ul>
        <li>
          Stranicu još nismo ispitali s čitačima zaslona (NVDA, VoiceOver) s
          korisnicima. Do tog ispitivanja ne možemo jamčiti da su svi grafikoni
          i tablice razumljivi pri slušanju.
        </li>
        <li>
          Nazivi stavki isplata, dobavljača i predmeta nabave prikazani su onako
          kako ih objavljuju gradovi i općine, ponekad velikim slovima ili sa
          skraćenicama koje nismo objasnili.
        </li>
      </ul>
      <h3>Sadržaj izvan opsega Zakona</h3>
      <ul>
        <li>
          Karte i datoteke trećih strana na koje upućujemo (OpenStreetMap,
          izvorni podaci javnih tijela) nisu pod našim nadzorom.
        </li>
      </ul>

      <h2>Što smo napravili</h2>
      <ul>
        <li>
          Uz svaki grafikon je rečenica koja kaže što pokazuje i tablica s istim
          podacima.
        </li>
        <li>
          Karta nije jedini način: svi gradovi i općine su i u popisu, a sve
          ustanove i u tekstu.
        </li>
        <li>
          Cijela stranica radi bez JavaScripta i s tipkovnicom, uz vidljiv fokus
          i poveznicu za preskakanje na sadržaj.
        </li>
        <li>
          Boje teksta imaju kontrast najmanje 4,5:1 u svijetlom i tamnom načinu.
        </li>
        <li>Stranica postoji i na jednostavnom jeziku te na engleskom.</li>
        <li>
          Svaka izmjena stranice automatski se provjerava alatom axe-core.
        </li>
      </ul>

      <h2>Priprema ove izjave</h2>
      <p>
        Izjava je sastavljena {date} na temelju samoprocjene, uz automatsku
        provjeru alatom axe-core i ručnu provjeru tipkovnicom. Izjava je
        posljednji put preispitana {date}
      </p>

      <h2>Povratne informacije i podaci za kontakt</h2>
      <p>
        Ako primijetite da nešto na stranici nije pristupačno, ili vam treba
        sadržaj u drugom obliku, javite nam se na{" "}
        <a href={`mailto:${email}`}>{email}</a>. Odgovorit ćemo u roku od 15
        dana.
      </p>

      <h2>Postupak praćenja provedbe</h2>
      <p>
        Ako niste zadovoljni našim odgovorom, ili vam ne odgovorimo u roku,
        možete se obratiti Povjereniku za informiranje, koji prati provedbu
        Zakona: <a href="https://www.pristupinfo.hr/">www.pristupinfo.hr</a>.
      </p>
    </>
  );
}
