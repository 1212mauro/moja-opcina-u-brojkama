import Link from "next/link";

import { routePath } from "@/lib/paths";
import { hrSimple } from "@/messages/hr-simple";

/** The methodology page in simple Croatian (D11, E2); see hr-methodology.tsx. */
export function MethodologyText({ leadClass }: { leadClass: string }) {
  return (
    <>
      <h1>Kako računamo</h1>
      <p className={leadClass}>
        Sve brojke su javne. Objavili su ih gradovi, općine i država. Mi ne
        kažemo je li potrošnja dobra ili loša. Pokazujemo brojke, a vi sami
        odlučite što mislite.
      </p>

      <h2>Odakle su brojke</h2>
      <ul>
        <li>
          <strong>Novac grada ili općine:</strong> izvještaji koje gradovi i
          općine šalju Ministarstvu financija. U njima piše koliko su novca
          dobili i potrošili u cijeloj godini.
        </li>
        <li>
          <strong>Broj stanovnika:</strong> popis stanovništva iz 2021. godine i
          procjene Državnog zavoda za statistiku.
        </li>
        <li>
          <strong>Ugovori za kupnju:</strong> popis ugovora na državnoj stranici
          za javnu nabavu (EOJN), popisi koje mjesta sama objavljuju i, za
          velike kupnje od 2024., europska stranica TED.
        </li>
        <li>
          <strong>Plaćanja:</strong> popisi plaćanja koje gradovi i općine
          objavljuju svaki mjesec.
        </li>
        <li>
          <strong>Škole, vrtići i liječnici:</strong> popisi Ministarstva
          znanosti, obrazovanja i mladih te karta OpenStreetMap.
        </li>
      </ul>
      <p>
        Brojke skidamo sami, svake noći. Popis svih izvora je na stranici{" "}
        <Link href={routePath("hr-simple", { page: "sources" })}>
          {hrSimple.site.nav.sources}
        </Link>
        .
      </p>

      <h2>Kako znamo čiji je podatak</h2>
      <p>
        Svaki grad i općina ima svoj broj (kod i OIB). Po tom broju znamo čiji
        je podatak, a ne po imenu. Vrtići, knjižnice i muzeji koje ima grad ili
        općina ubrojeni su u taj grad ili općinu. Škole i bolnice koje plaća
        županija ili država nisu ubrojene.
      </p>

      <h2>Koliko je to za svakog stanovnika</h2>
      <p>
        Uzmemo iznos i podijelimo ga s brojem stanovnika iste godine. Iznosi
        stariji od 2023. godine bili su u kunama. Pretvorili smo ih u eure:
        7,53450 kuna je 1 euro.
      </p>

      <h2>Usporedba sa sličnim mjestima</h2>
      <p>
        Grad uspoređujemo samo s gradovima, a općinu samo s općinama. Sva su
        mjesta iz iste županije i slične veličine. Veličine su: manje od 3.000
        stanovnika, od 3.000 do 10.000, od 10.000 do 35.000 i više od 35.000.
      </p>
      <p>
        Ako neko mjesto troši više, to ne znači da je loše. Mjesta s puno
        turista i mjesta koja grade nešto veliko često troše više. Mala mjesta
        imaju troškove koji su isti bez obzira na broj stanovnika.
      </p>

      <h2>Za što se troši novac</h2>
      <p>
        Grad ili općina sami pišu na što su potrošili novac: npr. na škole,
        ceste ili kulturu. Novac koji daju svojim vrtićima i knjižnicama tu nije
        ubrojen. Zato je ovaj zbroj manji od svega potrošenog novca.
      </p>

      <h2>Ugovori za kupnju</h2>
      <p>
        Iznosi ugovora su bez PDV-a (poreza koji se plaća kod kupnje). Kad se
        ugovor promijeni, ne brojimo ga kao novi ugovor. Neki ugovori nemaju
        objavljen iznos. Njih brojimo, ali ne zbrajamo njihov iznos.
      </p>

      <h2>Plaćanja i imena ljudi</h2>
      <p>
        Kad grad ili općina plati nekoj osobi, npr. plaću ili pomoć, ne
        pokazujemo ime ni OIB te osobe. Pokazujemo samo koliko je plaćeno svima
        zajedno. Ako ne znamo sigurno je li primatelj tvrtka, udruga ili
        ustanova, ne pokazujemo ni njegovo ime.
      </p>
      <p>
        Neka mjesta ne objavljuju plaćanja tako da ih možemo sami skinuti. Za ta
        mjesta plaćanja ne pokazujemo i to piše na njihovoj stranici.
      </p>

      <h2>Ako vidite grešku</h2>
      <p>
        Brojke pokazujemo onako kako su objavljene. Ako mislite da neka brojka
        nije točna, javite nam. Provjerit ćemo i ispraviti ili objasniti.
      </p>
    </>
  );
}
