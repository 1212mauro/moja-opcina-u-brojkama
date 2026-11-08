# Scenarij video predstavljanja

Video: `predstavljanje.mp4` (2:18, 1920×1080, s natpisima na zaslonu). Natpisi su i u `predstavljanje.srt`.

Pravila Datathona traže da video obuhvati: opis problema, ciljne korisnike, korištene izvore podataka, funkcionalnosti, tehničku arhitekturu, korisničku vrijednost i mogućnosti daljnjeg razvoja. Uz vrijeme svake scene piše koji od tih dijelova pokriva.

## Kako snimiti glas

1. Pustite video bez zvuka i čitajte uz njega; svaka scena počinje u označeno vrijeme. Vremena su izračunata za normalan tempo govora, pa tekst stane bez žurbe.
2. Snimajte mobitelom u tihoj prostoriji, oko 20 cm od usta. Na početku ostavite 2 sekunde tišine.
3. Ako jedna snimka ne ide, snimite svaku scenu kao zasebnu datoteku (`01.m4a`, `02.m4a`…); svaka se postavi na svoje vrijeme.

Video se ponovno snima iz izgrađene stranice (`web/`): `npm run build && node scripts/video.mjs ../docs/video`, pa pretvorba u MP4 (ffmpeg, H.264). Tada se i ovaj scenarij piše iznova, sa stvarnim vremenima.

## Scene

### 1. 0:00–0:10 · Problem

**Na zaslonu:** Naslovna kartica: „Moja općina u brojkama”, s pitanjem koje aplikacija rješava.

**Govor:** Koliko novca ima vaš grad ili općina i na što ga troši? Ti su podaci javni, ali razbacani po desetak službenih stranica i tablica koje je teško čitati.

### 2. 0:10–0:21 · Ciljni korisnici

**Na zaslonu:** Kartica „Za koga je?”: četiri skupine korisnika i što svaka dobiva.

**Natpis:** „Za koga je”

**Govor:** Moja općina u brojkama napravljena je za stanovnike koji žele znati kamo ide njihov novac, za vijećnike, novinare i udruge, i za same općine koje se žele usporediti sa sličnima.

### 3. 0:21–0:25 · Funkcionalnosti

**Na zaslonu:** Početna stranica. Pokazivač klikne u tražilicu i upiše „Lepo”; popis se suzi na Lepoglavu.

**Natpis:** „Upišite ime mjesta ili poštanski broj”

**Govor:** Na početnoj stranici upišete ime svog mjesta ili poštanski broj.

### 4. 0:25–0:30 · Funkcionalnosti

**Na zaslonu:** Klik na Lepoglavu; otvara se stranica grada.

**Natpis:** „Svaki grad i općina ima svoju stranicu”

**Govor:** Svaki od 28 gradova i općina Varaždinske županije ima svoju stranicu. Otvorimo Lepoglavu.

### 5. 0:30–0:37 · Funkcionalnosti

**Na zaslonu:** Zaglavlje stranice: ime, karta županije s označenom Lepoglavom i tri ključne brojke.

**Natpis:** „Najvažnije brojke odmah na vrhu”

**Govor:** Na vrhu su najvažnije brojke: koliko je grad prošle godine dobio i potrošio, i koliko je ugovora javne nabave sklopio.

### 6. 0:37–0:43 · Funkcionalnosti

**Na zaslonu:** Pokazivač na poveznici „21 % manje nego slična mjesta” ispod rashoda.

**Natpis:** „Usporedba sa sličnim mjestima”

**Govor:** Uz svaku brojku je i usporedba: Lepoglava po stanovniku troši 21 posto manje od sličnih gradova.

### 7. 0:43–0:50 · Funkcionalnosti

**Na zaslonu:** Pomicanje do odjeljka o proračunu: grafikoni prihoda po vrsti i rashoda po namjeni.

**Natpis:** „Odakle dolazi novac i na što se troši”

**Govor:** U dijelu o proračunu vidi se odakle novac dolazi i na što se troši, od obrazovanja do prometa.

### 8. 0:50–0:56 · Funkcionalnosti

**Na zaslonu:** Klik otvara tablicu s točnim iznosima ispod grafikona.

**Natpis:** „Uz svaki grafikon i tablica s brojkama”

**Govor:** Uz svaki grafikon je i tablica s točnim iznosima, pa brojke može pročitati i čitač zaslona.

### 9. 0:56–1:01 · Funkcionalnosti

**Na zaslonu:** Odjeljak „Usporedba”: Lepoglava uz slične jedinice, po stanovniku.

**Natpis:** „Usporedba s gradovima iste veličine”

**Govor:** Zatim slijedi usporedba s gradovima i općinama iste vrste i veličine u županiji.

### 10. 1:01–1:06 · Funkcionalnosti

**Na zaslonu:** Odjeljak „Javna nabava”: najveći dobavljači i najnoviji ugovori.

**Natpis:** „Javna nabava: od koga grad kupuje”

**Govor:** Javna nabava pokazuje od koga grad najviše kupuje i koji su najnoviji ugovori.

### 11. 1:06–1:12 · Funkcionalnosti

**Na zaslonu:** Odjeljak „Isplate”: iznosi po mjesecima i najveći primatelji.

**Natpis:** „Isplate iz proračuna: kome grad plaća”

**Govor:** Isplate pokazuju kome grad plaća, mjesec po mjesec. Imena privatnih osoba nikad se ne prikazuju.

### 12. 1:12–1:15 · Funkcionalnosti

**Na zaslonu:** Odjeljak „Ustanove”: škole, vrtići i zdravstvene ustanove.

**Natpis:** „Škole, vrtići i zdravstvo u blizini”

**Govor:** Tu su i škole, vrtići i ambulante u gradu.

### 13. 1:15–1:20 · Funkcionalnosti, izvori

**Na zaslonu:** Odjeljak „Izvori”: izdavač, poveznica, licenca i datum preuzimanja za svaki skup podataka.

**Natpis:** „Svaki broj ima izvor i datum preuzimanja”

**Govor:** Svaki broj ima izvor i datum preuzimanja, a podaci se osvježavaju automatski svake noći.

### 14. 1:20–1:31 · Izvori podataka

**Na zaslonu:** Kartica „Izvori podataka”: šest glavnih izdavača i čemu služe; ispod, kako su povezani.

**Natpis:** „16 skupova otvorenih podataka”

**Govor:** Podaci dolaze iz šesnaest skupova otvorenih podataka: Ministarstva financija, javne nabave, Zavoda za statistiku, Geodetske uprave, Portala otvorenih podataka i samih gradova. Povezujemo ih preko šifre općine i OIB-a.

### 15. 1:31–1:47 · Tehnička arhitektura

**Na zaslonu:** Kartica „Tehnička arhitektura”: Izvori → Python → JSON → Next.js → GitHub Pages.

**Natpis:** „Tehnička arhitektura”

**Govor:** Arhitektura je jednostavna. Svake noći program u Pythonu preuzima izvore, obrađuje ih i provjerava kvalitetu. Iz toga nastaje JSON za svaku općinu, a Next.js od njega gradi statičke stranice. Nema poslužitelja ni baze. Ako neki izvor ne radi, ostaju njegovi zadnji ispravni podaci.

### 16. 1:47–1:53 · Funkcionalnosti

**Na zaslonu:** Klik na „Obični jezik”, zatim na „English”: ista stranica u druga dva izdanja.

**Natpis:** „Jednostavnim jezikom, i na engleskom”

**Govor:** Cijela stranica postoji i na jednostavnom jeziku, za one kojima je službeni jezik težak, te na engleskom.

### 17. 1:53–1:59 · Funkcionalnosti

**Na zaslonu:** Dva mobitela jedan uz drugi: stranica Lepoglave u svijetlom i u tamnom načinu.

**Natpis:** „Pristupačno: WCAG 2.1 AA, i na mobitelu”

**Govor:** Radi na mobitelu, u svijetlom i tamnom načinu, i zadovoljava standard pristupačnosti WCAG 2.1 AA.

### 18. 1:59–2:08 · Daljnji razvoj

**Na zaslonu:** Kartica „Daljnji razvoj”: četiri sljedeća koraka.

**Natpis:** „Daljnji razvoj”

**Govor:** Sljedeći koraci su svih 556 gradova i općina u Hrvatskoj, svi ugovori od 2024. preko API-ja javne nabave, isplate za više mjesta i testiranje sa stanovnicima.

### 19. 2:08–2:18 · Korisnička vrijednost

**Na zaslonu:** Završna kartica: adresa stranice, opseg i licenca.

**Govor:** U minuti dobijete odgovor za koji biste inače pretražili desetak stranica. Danas 28 gradova i općina Varaždinske županije, a cilj je svih 556. Otvoreni podaci, otvoreni kod.

## Cijeli tekst za čitanje

Koliko novca ima vaš grad ili općina i na što ga troši? Ti su podaci javni, ali razbacani po desetak službenih stranica i tablica koje je teško čitati.

Moja općina u brojkama napravljena je za stanovnike koji žele znati kamo ide njihov novac, za vijećnike, novinare i udruge, i za same općine koje se žele usporediti sa sličnima.

Na početnoj stranici upišete ime svog mjesta ili poštanski broj.

Svaki od 28 gradova i općina Varaždinske županije ima svoju stranicu. Otvorimo Lepoglavu.

Na vrhu su najvažnije brojke: koliko je grad prošle godine dobio i potrošio, i koliko je ugovora javne nabave sklopio.

Uz svaku brojku je i usporedba: Lepoglava po stanovniku troši 21 posto manje od sličnih gradova.

U dijelu o proračunu vidi se odakle novac dolazi i na što se troši, od obrazovanja do prometa.

Uz svaki grafikon je i tablica s točnim iznosima, pa brojke može pročitati i čitač zaslona.

Zatim slijedi usporedba s gradovima i općinama iste vrste i veličine u županiji.

Javna nabava pokazuje od koga grad najviše kupuje i koji su najnoviji ugovori.

Isplate pokazuju kome grad plaća, mjesec po mjesec. Imena privatnih osoba nikad se ne prikazuju.

Tu su i škole, vrtići i ambulante u gradu.

Svaki broj ima izvor i datum preuzimanja, a podaci se osvježavaju automatski svake noći.

Podaci dolaze iz šesnaest skupova otvorenih podataka: Ministarstva financija, javne nabave, Zavoda za statistiku, Geodetske uprave, Portala otvorenih podataka i samih gradova. Povezujemo ih preko šifre općine i OIB-a.

Arhitektura je jednostavna. Svake noći program u Pythonu preuzima izvore, obrađuje ih i provjerava kvalitetu. Iz toga nastaje JSON za svaku općinu, a Next.js od njega gradi statičke stranice. Nema poslužitelja ni baze. Ako neki izvor ne radi, ostaju njegovi zadnji ispravni podaci.

Cijela stranica postoji i na jednostavnom jeziku, za one kojima je službeni jezik težak, te na engleskom.

Radi na mobitelu, u svijetlom i tamnom načinu, i zadovoljava standard pristupačnosti WCAG 2.1 AA.

Sljedeći koraci su svih 556 gradova i općina u Hrvatskoj, svi ugovori od 2024. preko API-ja javne nabave, isplate za više mjesta i testiranje sa stanovnicima.

U minuti dobijete odgovor za koji biste inače pretražili desetak stranica. Danas 28 gradova i općina Varaždinske županije, a cilj je svih 556. Otvoreni podaci, otvoreni kod.
