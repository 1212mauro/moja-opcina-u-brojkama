# Naracija za video predstavljanje

Video: `predstavljanje.mp4` (1:49, 1920×1080, bez zvuka, s natpisima). Natpisi su i u `predstavljanje.srt`.

Čitajte svaki odlomak od označenog vremena, normalnim tempom govora; vremena su izračunata tako da tekst stane. Glas možete snimiti mobitelom ili u bilo kojem programu za video (npr. Clipchamp, CapCut, DaVinci Resolve) i staviti ga ispod videa.

Video se ponovno snima iz izgrađene stranice (`web/`): `npm run build && node scripts/video.mjs ../docs/video`, pa pretvorba u MP4 (ffmpeg, H.264).

**0:00–0:07**

Koliko novca ima vaš grad i na što ga troši? Podaci su javni, ali razbacani po desetak službenih stranica.

**0:07–0:15** · natpis: „Za koga je”

Za stanovnike koji žele znati kamo ide njihov novac, za vijećnike, novinare i udruge, i za same općine koje se žele usporediti sa sličnima.

**0:16–0:20** · natpis: „Upišite ime mjesta ili poštanski broj”

Ovdje su na jednom mjestu. Upišite ime mjesta ili poštanski broj.

**0:20–0:23** · natpis: „Svaki grad i općina ima svoju stranicu”

Svaki grad i općina ima svoju stranicu.

**0:23–0:26** · natpis: „Najvažnije brojke odmah na vrhu”

Na vrhu su prihodi, rashodi i broj ugovora javne nabave.

**0:26–0:31** · natpis: „Usporedba sa sličnim mjestima”

I usporedba: Lepoglava po stanovniku troši 21 posto manje od sličnih gradova.

**0:31–0:35** · natpis: „Odakle dolazi novac i na što se troši”

Proračun: odakle novac dolazi i na što se troši.

**0:35–0:38** · natpis: „Uz svaki grafikon i tablica s brojkama”

Uz svaki grafikon je i tablica s točnim iznosima.

**0:38–0:41** · natpis: „Usporedba s gradovima iste veličine”

Usporedba s gradovima iste veličine u županiji.

**0:41–0:44** · natpis: „Javna nabava: od koga grad kupuje”

Javna nabava: najveći dobavljači i najnoviji ugovori.

**0:44–0:49** · natpis: „Isplate iz proračuna: kome grad plaća”

Isplate: kome grad plaća, mjesec po mjesec. Privatne osobe su bez imena.

**0:49–0:51** · natpis: „Škole, vrtići i zdravstvo u blizini”

Škole, vrtići i ambulante u gradu.

**0:51–0:55** · natpis: „Svaki broj ima izvor i datum preuzimanja”

Svaki broj ima izvor, a podaci se osvježavaju automatski svake noći.

**0:55–1:06** · natpis: „16 skupova otvorenih podataka”

Podaci dolaze iz šesnaest skupova podataka: Ministarstva financija, javne nabave, Zavoda za statistiku, Geodetske uprave, Portala otvorenih podataka i samih gradova. Povezujemo ih preko šifre općine i OIB-a.

**1:06–1:21** · natpis: „Tehnička arhitektura”

Arhitektura je jednostavna. Svake noći program u Pythonu preuzima izvore, obrađuje ih i provjerava kvalitetu. Iz toga nastaje JSON za svaku općinu, a Next.js od njega gradi statičke stranice. Nema poslužitelja ni baze. Ako neki izvor ne radi, ostaju njegovi zadnji ispravni podaci.

**1:21–1:26** · natpis: „Jednostavnim jezikom, i na engleskom”

Sve je i na jednostavnom jeziku, te na engleskom.

**1:26–1:31** · natpis: „Pristupačno: WCAG 2.1 AA, i na mobitelu”

Radi na mobitelu, u svijetlom i tamnom načinu, i zadovoljava WCAG 2.1 AA.

**1:31–1:39** · natpis: „Daljnji razvoj”

Sljedeći koraci: svih 556 gradova i općina, ugovori od 2024. preko API-ja javne nabave, isplate za više mjesta i testiranje sa stanovnicima.

**1:39–1:49**

U minuti dobijete odgovor za koji biste inače pretražili desetak stranica. Danas 28 gradova i općina Varaždinske županije, a cilj je svih 556. Otvoreni podaci, otvoreni kod.
