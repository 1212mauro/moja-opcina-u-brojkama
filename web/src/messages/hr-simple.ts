/**
 * Croatian in simple language (E2): short sentences and everyday words, at roughly
 * a primary-school reading level ("novac za ceste" rather than "rashodi za cestovni
 * promet"). Only the text that differs from hr.ts is written here.
 */
import { hr, plural, type Messages } from "@/messages/hr";

export const hrSimple: Messages = {
  ...hr,

  site: {
    ...hr.site,
    tagline:
      "Koliko novca ima vaše mjesto, na što ga troši i gdje su škole, vrtići i liječnici.",
    editions: {
      label: "Jezik",
      links: { hr: "Obični jezik", en: "English" },
    },
    footer: {
      ...hr.site.footer,
      about:
        "Ovu stranicu ne radi nijedna tvrtka ni stranka. Pokazujemo samo brojke koje su gradovi, općine i država već objavili. Ne kažemo je li potrošnja dobra ili loša.",
    },
  },

  home: {
    ...hr.home,
    intro:
      "Ovdje vidite koliko novca ima vaš grad ili općina, na što ga troši i što kupuje. Vidite i usporedbu sa sličnim mjestima.",
    searchHint:
      "Upišite ime mjesta, npr. „Lepoglava”, ili poštanski broj, npr. „42250”",
    noResults: "Nema grada ni općine s tim imenom ili brojem.",
  },

  page: {
    ...hr.page,
    keyFigures: "Najvažnije brojke",
    revenue: (year: number) => `Novac koji je dobio ${year}.`,
    expenditure: (year: number) => `Novac koji je potrošio ${year}.`,
    perResident: (value: string) => `${value} za svakog stanovnika`,
    contracts: "Ugovori za kupnju",
  },

  sections: {
    budget: "Koliko novca ima i troši",
    peers: "Usporedba sa sličnim mjestima",
    procurement: "Što kupuje i od koga",
    payments: "Kome plaća",
    facilities: "Škole, vrtići i liječnici",
    sources: "Odakle su podaci",
  },

  budget: {
    ...hr.budget,
    intro: (year: number) =>
      `Ovo je novac koji je mjesto stvarno dobilo i potrošilo u ${year}. godini. Podatke mjesto šalje Ministarstvu financija.`,
    revenueByType: "Odakle dolazi novac",
    expenditureByFunction: "Za što se troši novac",
    revenueSummary: (top: string, share: string) =>
      `Najviše novca dolazi od stavke „${top}” (${share} svega novca).`,
    functionSummary: (top: string, share: string) =>
      `Najviše novca ide na stavku „${top}” (${share}).`,
    functionNote:
      "Ovdje nije novac koji mjesto daje svojim vrtićima, knjižnicama i drugim ustanovama. Taj novac troši sama ustanova.",
    revenueLabels: {
      "61": "Porezi",
      "62": "Doprinosi",
      "63": "Novac od države, županije i Europske unije",
      "64": "Najam zemljišta i zgrada, kamate",
      "65": "Pristojbe i naknade, npr. komunalna naknada",
      "66": "Prodaja usluga i pokloni u novcu",
      "67": "Novac iz proračuna",
      "68": "Kazne i ostalo",
      "71": "Prodaja zemljišta",
      "72": "Prodaja zgrada, stanova i opreme",
    },
    functionLabels: {
      "01": "Rad uprave i vijeća",
      "02": "Obrana",
      "03": "Vatrogasci i sigurnost",
      "04": "Ceste, promet i gospodarstvo",
      "05": "Smeće, otpadne vode i priroda",
      "06": "Uređenje mjesta: rasvjeta, voda, parkovi",
      "07": "Zdravlje",
      "08": "Sport, kultura i vjerske zajednice",
      "09": "Vrtići i škole",
      "10": "Pomoć ljudima kojima je potrebna",
    },
    columns: {
      item: "Za što",
      amount: "Iznos",
      perResident: "Za svakog stanovnika",
      share: "Dio od svega",
    },
  },

  peers: {
    ...hr.peers,
    intro: (typePlural: string, band: string, county: string, count: number) =>
      `Uspoređujemo samo slična mjesta iz iste županije (${county}): ${typePlural} s ${band}.` +
      (count > 1 ? ` Takvih mjesta je ${count}, s ovim zajedno.` : ""),
    alone:
      "U ovoj županiji nema drugog sličnog mjesta, pa ne možemo usporediti.",
    chartTitle: "Koliko potroši za svakog stanovnika",
    rank: (rank: number, of: number) =>
      rank === 1
        ? `od ${of} sličnih mjesta najviše troši za svakog stanovnika`
        : rank === of
          ? `od ${of} sličnih mjesta najmanje troši za svakog stanovnika`
          : `je od ${of} sličnih mjesta na ${rank}. mjestu po tome koliko troši za svakog stanovnika`,
    summary: (name: string, rank: string) => `${name} ${rank}.`,
    context:
      "Više potrošenog novca ne znači da je nešto dobro ili loše. Mjesta s puno turista, veliki gradovi i mjesta koja grade nešto veliko često troše više.",
    columns: {
      ...hr.peers.columns,
      revenue: "Dobiveno za svakog stanovnika",
      expenditure: "Potrošeno za svakog stanovnika",
    },
  },

  procurement: {
    ...hr.procurement,
    intro: (count: number, formatted: string, from: string, to: string) =>
      `Od ${from} do ${to} mjesto je potpisalo ${formatted} ${plural(count, "ugovor", "ugovora", "ugovora")} za kupnju robe, usluga i radova. Tu su i ugovori njegovih vrtića, knjižnica i drugih ustanova.`,
    total: "Vrijednost svih ugovora (bez poreza PDV)",
    recent: "Zadnji ugovori",
    topSuppliers: "Od koga najviše kupuje",
    // Suppliers are not always companies (associations, crafts, public bodies).
    topSuppliersSummary: (name: string, share: string) =>
      `Najviše kupuje od: ${name} (${share} vrijednosti svih ugovora).`,
    topSupplierName: (name: string) => `Najviše kupuje od: ${name}.`,
    noValue: "iznos nije objavljen",
    columns: {
      ...hr.procurement.columns,
      subject: "Što se kupuje",
      supplier: "Od koga",
      value: "Iznos bez PDV-a",
    },
  },

  payments: {
    ...hr.payments,
    intro: (from: string, to: string) =>
      `Ovo su plaćanja od ${from} do ${to}. Mjesto ih objavljuje svaki mjesec.`,
    monthly: "Koliko plati svaki mjesec",
    categories: "Za što plaća",
    categoriesSummary: (label: string) =>
      `Najviše novca otišlo je na stavku „${label}”.`,
    recipients: "Kome najviše plaća",
    recipientsSummary: (name: string, amount: string) =>
      `Najviše novca dobio je ${name}: ${amount}.`,
    privacy:
      "Kad mjesto plati nekoj osobi, npr. plaću ili pomoć, ne pokazujemo ime te osobe. Pokazujemo samo koliko je plaćeno svima zajedno.",
  },

  facilities: {
    ...hr.facilities,
    intro: (count: number) =>
      `Broj škola, vrtića, liječnika i ljekarni u ovom mjestu: ${count}.`,
    types: {
      school: "Škole",
      kindergarten: "Vrtići",
      health: "Liječnici i ljekarne",
    },
  },

  missing: {
    budget: "Za ovo mjesto još nemamo podatke o novcu.",
    peers: "Ne možemo usporediti jer nemamo podatke o novcu.",
    procurement: "Za ovo mjesto nismo našli ugovore za kupnju.",
    payments:
      "Za ovo mjesto još ne pokazujemo plaćanja. Pokazujemo ih samo kad ih mjesto objavi tako da ih svatko može preuzeti.",
    facilities: "Za ovo mjesto nismo našli škole, vrtiće ni liječnike.",
  },

  sources: {
    ...hr.sources,
    intro:
      "Svaka brojka na ovoj stranici dolazi s jednog od ovih mjesta. Podatke skidamo sami, svake noći.",
  },
};
