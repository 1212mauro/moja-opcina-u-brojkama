/**
 * Croatian UI text. Every user-facing string lives in messages/: short strings here,
 * long prose as one component per edition (methodology/, accessibility/). English
 * (en.ts) and simple language (hr-simple.ts) have the same shape: `Messages`.
 */
import type { MunicipalityPage } from "@/lib/contract";
import type { Locale } from "@/lib/i18n";

type UnitType = MunicipalityPage["type"];

/**
 * Croatian noun form after a number: 1, 21, 31 take ``one``; 2-4, 22-24 take ``few``;
 * 5-20, 25-30 and 11-14 take ``many`` ("1 ugovor", "3 ugovora", "12 ugovora").
 */
export function plural(
  n: number,
  one: string,
  few: string,
  many: string,
): string {
  const last = n % 10;
  const lastTwo = n % 100;
  if (last === 1 && lastTwo !== 11) return one;
  if (last >= 2 && last <= 4 && (lastTwo < 12 || lastTwo > 14)) return few;
  return many;
}

type Band = MunicipalityPage["band"];

const units = (n: number) =>
  plural(
    n,
    "usporedive jedinice",
    "usporedive jedinice",
    "usporedivih jedinica",
  );

export const hr = {
  site: {
    name: "Moja općina u brojkama",
    tagline:
      "Kako vaš grad ili općina troši novac, što nabavlja i koje su javne usluge u blizini.",
    skipToContent: "Preskoči na sadržaj",
    nav: {
      label: "Glavna navigacija",
      home: "Početna",
      methodology: "Kako računamo",
      sources: "Izvori podataka",
      accessibility: "Pristupačnost",
    },
    // Links to the other editions, in the words of this one.
    editions: {
      label: "Jezik",
      links: {
        "hr-simple": "Jednostavni jezik",
        en: "English",
      } as Partial<Record<Locale, string>>,
    },
    footer: {
      about:
        "Nekomercijalni projekt otvorenog koda. Prikazujemo samo podatke koje su javna tijela već objavila i ne ocjenjujemo je li potrošnja dobra ili loša.",
      licence:
        "Izvorni kod: EUPL-1.2. Podaci: Otvorena dozvola Republike Hrvatske, CC BY i ODbL (OpenStreetMap).",
    },
  },

  home: {
    title: "Pronađite svoju općinu ili grad",
    intro:
      "Za svaku općinu i grad pokazujemo proračun, javnu nabavu, isplate i javne usluge na jednom mjestu te ih uspoređujemo sa sličnima u istoj županiji.",
    searchLabel: "Naziv ili poštanski broj",
    searchHint: "Npr. „Ludbreg” ili „42230”",
    // "Rezultata: 2" avoids Croatian's number agreement (1 grad, 2 grada, 5 gradova).
    resultsCount: (n: number) => `Rezultata: ${n}`,
    noResults: "Nijedna općina ni grad ne odgovaraju upisanom pojmu.",
    tableCaption: (county: string) => `Gradovi i općine: ${county} županija`,
    allUnits: "Gradovi i općine",
    columns: {
      name: "Naziv",
      type: "Vrsta",
      population: "Stanovnika",
      postcodes: "Poštanski brojevi",
    },
  },

  unitType: { grad: "Grad", opcina: "Općina" } satisfies Record<
    UnitType,
    string
  >,
  unitTypePlural: { grad: "gradovi", opcina: "općine" } satisfies Record<
    UnitType,
    string
  >,
  band: {
    under_3k: "manje od 3.000 stanovnika",
    "3k_10k": "3.000 do 10.000 stanovnika",
    "10k_35k": "10.000 do 35.000 stanovnika",
    over_35k: "više od 35.000 stanovnika",
  } satisfies Record<Band, string>,

  page: {
    breadcrumb: "Putokaz",
    county: (county: string): string => `${county} županija`,
    population: (total: string, year: number, estimate: boolean) =>
      `${total} stanovnika (${estimate ? "procjena" : "popis"} ${year}.)`,
    contents: "Na ovoj stranici",
    keyFigures: "Ukratko",
    revenue: (year: number) => `Prihodi ${year}.`,
    expenditure: (year: number) => `Rashodi ${year}.`,
    perResident: (value: string) => `${value} po stanovniku`,
    contracts: "Ugovori javne nabave",
    contractsSince: (from: string) => `od ${from}`,
  },

  sections: {
    budget: "Proračun",
    peers: "Usporedba sa sličnima",
    procurement: "Javna nabava",
    payments: "Isplate iz proračuna",
    facilities: "Škole, vrtići i zdravstvo",
    sources: "Izvori podataka",
  },

  budget: {
    intro: (year: number) =>
      `Ostvareni prihodi i rashodi u ${year}. godini, prema financijskom izvještaju koji jedinica predaje Ministarstvu financija.`,
    revenueByType: "Odakle dolazi novac",
    expenditureByFunction: "Na što se troši",
    revenueSummary: (top: string, share: string) =>
      `Najveći izvor prihoda su ${top.toLowerCase()} (${share} svih prihoda).`,
    functionSummary: (top: string, share: string) =>
      `Najviše se troši na ${top.toLowerCase()} (${share} rashoda raspoređenih po namjeni).`,
    functionNote:
      "Rashodi po namjeni ne uključuju novac koji grad ili općina prenosi vlastitim ustanovama (vrtićima, knjižnicama…); taj se novac ovdje vidi kod ustanove koja ga troši.",
    // Labels by code when an edition words them differently from the data
    // (official Croatian names); empty means the data's own label.
    revenueLabels: {} as Record<string, string>,
    functionLabels: {} as Record<string, string>,
    columns: {
      item: "Stavka",
      amount: "Iznos",
      perResident: "Po stanovniku",
      share: "Udio",
    },
  },

  peers: {
    intro: (typePlural: string, band: string, county: string, count: number) =>
      `Slične jedinice su ${typePlural} iz iste županije (${county}) s ${band}.` +
      (count > 1 ? ` Takvih je ${count}, uključujući ovu.` : ""),
    alone:
      "U ovoj županiji nema druge jedinice iste vrste i veličine, pa usporedba nije moguća.",
    chartTitle: "Rashodi po stanovniku",
    rank: (rank: number, of: number) =>
      rank === 1
        ? `najviše od ${of} ${units(of)}`
        : rank === of
          ? `najmanje od ${of} ${units(of)}`
          : `${rank}. najviše od ${of} ${units(of)}`,
    summary: (name: string, rank: string) =>
      `${name} po stanovniku troši ${rank}.`,
    thisUnit: "(ova jedinica)",
    context:
      "Usporedba po stanovniku ne govori je li potrošnja dobra ili loša. Turističke općine, sjedišta županija i jedinice s velikim investicijama često troše više po stanovniku.",
    columns: {
      name: "Grad ili općina",
      population: "Stanovnika",
      revenue: "Prihodi po stanovniku",
      expenditure: "Rashodi po stanovniku",
    },
  },

  procurement: {
    intro: (count: number, formatted: string, from: string, to: string) =>
      `${formatted} ${plural(count, "ugovor", "ugovora", "ugovora")} javne nabave od ${from} do ${to}, uključujući ugovore vlastitih ustanova (vrtića, knjižnica…).`,
    contractCount: (count: number, formatted: string) =>
      `${formatted} ${plural(count, "ugovor", "ugovora", "ugovora")}`,
    total: "Ukupna vrijednost ugovora (bez PDV-a)",
    recent: "Najnoviji ugovori",
    topSuppliers: "Najveći dobavljači",
    topSuppliersSummary: (name: string, share: string) =>
      `Najveći dobavljač je ${name} s ${share} ukupne vrijednosti ugovora.`,
    topSupplierName: (name: string) => `Najveći dobavljač je ${name}.`,
    noValue: "iznos nije objavljen",
    columns: {
      date: "Datum",
      subject: "Predmet",
      supplier: "Dobavljač",
      value: "Vrijednost bez PDV-a",
      contracts: "Ugovora",
      total: "Ukupno",
    },
  },

  payments: {
    intro: (from: string, to: string) =>
      `Isplate iz proračuna od ${from} do ${to}, kako ih grad ili općina objavljuje svaki mjesec.`,
    monthly: "Isplate po mjesecima",
    monthlySummary: (total: string, months: number) =>
      `Ukupno ${total} u ${months} ${plural(months, "mjesecu", "mjeseca", "mjeseci")} s objavljenim podacima.`,
    missingMonth: "nije objavljeno",
    categories: "Za što se plaća",
    categoriesSummary: (label: string) =>
      `Najviše je plaćeno za stavku „${label}”.`,
    recipients: "Najveći primatelji",
    recipientsSummary: (name: string, amount: string) =>
      `Najviše novca primio je ${name} (${amount}).`,
    // The categories are the publisher's own words; other languages say so.
    labelsNote: "",
    privacy:
      "Isplate fizičkim osobama prikazujemo samo zbirno, bez imena, kako propisuju pravila o objavi i zaštiti osobnih podataka.",
    columns: {
      month: "Mjesec",
      amount: "Iznos",
      category: "Vrsta rashoda",
      recipient: "Primatelj",
      payments: "Isplata",
    },
  },

  facilities: {
    intro: (count: number) =>
      `${count} ${plural(count, "javna ustanova", "javne ustanove", "javnih ustanova")} na području ove jedinice.`,
    types: {
      school: "Škole",
      kindergarten: "Vrtići",
      health: "Zdravstvo i ljekarne",
    },
    address: "Adresa",
    noAddress: "adresa nije navedena",
    mapLink: "Prikaži na karti",
  },

  map: {
    home: "Karta: kliknite grad ili općinu, ili ih odaberite iz popisa ispod.",
    locator: (name: string) => `Položaj: ${name} u županiji`,
    noData: "podaci još nisu dostupni",
  },

  missing: {
    budget: "Za ovu jedinicu još nemamo podatke o proračunu.",
    peers: "Usporedba nije dostupna jer nemamo podatke o proračunu.",
    procurement:
      "Za ovu jedinicu nismo pronašli objavljene ugovore javne nabave.",
    payments:
      "Ova jedinica ne objavljuje isplate u obliku koji možemo automatski preuzeti (npr. kao tablicu ili otvorene podatke), pa ih ne prikazujemo.",
    facilities:
      "Za ovu jedinicu nismo pronašli škole, vrtiće ni zdravstvene ustanove.",
  },

  notFound: {
    title: "Stranica nije pronađena",
    body: "Ova adresa ne postoji. Možda je pogrešno upisana ili je stranica premještena.",
    home: "Pronađite svoju općinu ili grad na početnoj stranici",
  },

  figure: {
    showTable: "Prikaži podatke kao tablicu",
    source: "Izvor",
    // Follows the source title, which is set apart for its lang attribute.
    retrieved: (date: string) => `preuzeto ${date}`,
  },

  sources: {
    intro:
      "Svaki broj na ovoj stranici dolazi iz jednog od ovih izvora. Podatke preuzimamo automatski, svake noći.",
    columns: {
      source: "Izvor",
      publisher: "Objavio",
      fetched: "Preuzeto",
      rows: "Zapisa",
      licence: "Licenca",
    },
    generated: (date: string) => `Podaci na stranici složeni su ${date}`,
    // Licence descriptions by source id when an edition words them differently
    // from the data (which is in Croatian); empty means the data's own text.
    licences: {} as Record<string, string>,
    status: {
      failed: "zadnje preuzimanje nije uspjelo; prikazujemo prethodne podatke",
      skipped: "još ne preuzimamo: čekamo pristup izvoru",
      unavailable: "izvor nije dostupan u strojno čitljivom obliku",
    },
  },
};

export type Messages = typeof hr;
