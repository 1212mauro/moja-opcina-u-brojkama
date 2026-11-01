import Link from "next/link";

import { routePath } from "@/lib/paths";
import { hr } from "@/messages/hr";

/**
 * The methodology page's text in Croatian (D11). Long prose lives here rather than
 * in hr.ts; an English version is a sibling file with the same export.
 */
export function MethodologyText({ leadClass }: { leadClass: string }) {
  return (
    <>
      <h1>Kako računamo</h1>
      <p className={leadClass}>
        Svi brojevi dolaze iz javno objavljenih podataka. Ne ocjenjujemo je li
        potrošnja dobra ili loša: pokazujemo brojke i usporedbe, a tumačenje
        ostavljamo vama.
      </p>

      <h2>Odakle su podaci</h2>
      <ul>
        <li>
          <strong>Proračun:</strong> financijski izvještaji gradova i općina
          koje objavljuje Ministarstvo financija (ostvareni prihodi i rashodi za
          cijelu godinu).
        </li>
        <li>
          <strong>Stanovništvo:</strong> Popis stanovništva 2021. i godišnje
          procjene Državnog zavoda za statistiku.
        </li>
        <li>
          <strong>Javna nabava:</strong> registri ugovora u Elektroničkom
          oglasniku javne nabave (EOJN RH).
        </li>
        <li>
          <strong>Isplate:</strong> mjesečne objave isplata iz proračuna koje
          gradovi i općine objavljuju prema Naputku (NN 59/23).
        </li>
        <li>
          <strong>Škole, vrtići i zdravstvo:</strong> upisnici Ministarstva
          znanosti, obrazovanja i mladih te OpenStreetMap.
        </li>
      </ul>
      <p>
        Podatke preuzimamo automatski, svake noći. Popis izvora s datumom
        zadnjeg preuzimanja je na stranici{" "}
        <Link href={routePath("hr", { page: "sources" })}>
          {hr.site.nav.sources}
        </Link>
        .
      </p>

      <h2>Kako povezujemo podatke</h2>
      <p>
        Svaki podatak vezan je uz grad ili općinu preko njezina službenog koda i
        OIB-a, a ne preko naziva. Ugovori i isplate vlastitih ustanova grada ili
        općine (dječjih vrtića, knjižnica, muzeja) pribrajaju se tom gradu ili
        općini, prema Registru proračunskih korisnika Ministarstva financija.
        Škole i bolnice koje financira županija ili država ne pribrajaju se.
      </p>

      <h2>Iznosi po stanovniku</h2>
      <p>
        Iznos po stanovniku je iznos podijeljen brojem stanovnika iste godine
        (procjena Državnog zavoda za statistiku, a ako je nema, popis). Iznosi
        iz razdoblja prije 2023. preračunati su u eure po fiksnom tečaju 7,53450
        kuna za euro.
      </p>

      <h2>Usporedba sa sličnima</h2>
      <p>
        Grad ili općinu uspoređujemo s jedinicama iste vrste (grad s gradovima,
        općinu s općinama) iz iste županije i slične veličine. Razredi veličine
        su: manje od 3.000 stanovnika, 3.000 do 10.000, 10.000 do 35.000 i više
        od 35.000.
      </p>
      <p>
        Usporedba po stanovniku nije ocjena. Turističke općine, sjedišta
        županija i jedinice koje tek grade veliku investiciju često troše više
        po stanovniku; male općine imaju troškove koji ne rastu s brojem
        stanovnika.
      </p>

      <h2>Rashodi po namjeni</h2>
      <p>
        Rashode po namjeni (obrazovanje, zaštita okoliša, kultura…) prikazujemo
        kako ih gradovi i općine razvrstavaju u izvještaju. Ta podjela ne
        uključuje novac koji grad ili općina prenosi vlastitim ustanovama; zato
        je zbroj po namjeni manji od ukupnih rashoda.
      </p>

      <h2>Javna nabava</h2>
      <p>
        Vrijednosti ugovora su bez PDV-a. Dodaci i izmjene ugovora mijenjaju
        ukupnu vrijednost, ali ih ne brojimo kao nove ugovore. Neki ugovori u
        registru nemaju objavljen iznos; brojimo ih, ali ne pribrajamo
        vrijednosti.
      </p>

      <h2>Isplate i osobni podaci</h2>
      <p>
        Isplate fizičkim osobama (plaće, naknade, pomoći građanima) prikazujemo
        samo zbirno, po vrsti rashoda, bez imena i OIB-a. Ako za primatelja ne
        možemo potvrditi da je tvrtka, udruga ili javna ustanova, njegovo ime ne
        prikazujemo. Opise isplata ne prikazujemo jer mogu sadržavati imena.
      </p>
      <p>
        Neki gradovi i općine isplate objavljuju samo u obliku koji ne možemo
        automatski preuzeti; za njih isplate ne prikazujemo i to jasno navodimo
        na njihovoj stranici.
      </p>

      <h2>Ako uočite pogrešku</h2>
      <p>
        Prikazujemo podatke onako kako su objavljeni. Ako mislite da je broj
        pogrešan, a pogotovo ako predstavljate grad ili općinu, javite nam se pa
        ćemo provjeriti izvor i ispraviti prikaz ili objasniti razliku.
      </p>
    </>
  );
}
