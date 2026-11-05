# Zahtjev: API ključ za Open Data API EOJN RH

> **Draft, not sent.** Asks Narodne novine (EOJN RH) for an `X-API-Key` for the read-only Open Data API, so the pipeline can fetch contracts from 2024 onwards. It also discloses the weekly reading of the old public contract register and asks whether that is acceptable. `eojn@nn.hr` is the address published on eojn.hr and eojn.nn.hr. Fill in the `[…]` fields before sending; when the key arrives, add it as the repository secret `EOJN_API_KEY`.

**Za:** eojn@nn.hr
**Predmet:** Zahtjev za API ključ – Open Data API EOJN RH (registar ugovora, nekomercijalna uporaba)

---

Poštovani,

obraćamo vam se kao [naziv tima / udruge] koji u sklopu [naziv datathona] razvija otvorenu, nekomercijalnu web-aplikaciju **„Moja općina u brojkama”**. Aplikacija građanima jednostavnim jezikom prikazuje proračun, javnu nabavu i javne usluge njihovog grada ili općine te ih uspoređuje sa sličnim jedinicama u istoj županiji. U pilot-fazi obuhvaćamo Varaždinsku županiju: 28 gradova i općina i njihove proračunske korisnike, ukupno 67 naručitelja prema OIB-u. Kasnije planiramo obuhvatiti svih 556 jedinica. Izvorni kod objavljujemo pod licencom EUPL-1.2.

Molimo vas za **API ključ (`X-API-Key`) za Open Data API** opisan u vašoj OpenAPI specifikaciji. Koristili bismo isključivo metode za čitanje:

- `GET /api/public/eContractRegister/contractsSearch` (ugovori objavljeni u vremenskom razdoblju),
- `GET /api/public/eProcurementData/eventsForContractsByTime` (izmjene ugovora u razdoblju),
- `GET /api/public/eProcurementData/getContractData` (podaci pojedinog ugovora čija se izmjena dogodila).

Način korištenja:

- jednom noćno (oko 03:30 UTC), u tjednim vremenskim prozorima, uz **najviše jedan upit svakih 6 sekundi**;
- početno preuzimanje od 1. 1. 2024. raspoređeno je na nekoliko noći (najviše 26 tjednih prozora po noći);
- zadržavamo samo ugovore naručitelja iz našeg obuhvata;
- svaki upit nosi User-Agent `moja-opcina-u-brojkama/0.1 (+https://github.com/1212mauro/moja-opcina-u-brojkama)`;
- ključ čuvamo kao tajnu u GitHub Actions i nikad ga ne objavljujemo.

Javnu tražilicu na eojn.hr ne koristimo automatizirano jer njezin robots.txt to ne dopušta.

Radi transparentnosti: ugovore iz razdoblja 2018. – 2023. preuzimamo iz javnog izvješća „Registar ugovora” starog sustava (`eojn.nn.hr/Spin/application/ipn/JavniReporti/RptRegistarUgovora.aspx`). To radimo jednom tjedno, za svakog od 67 naručitelja, preko izvoza u Excel, uz stanku od 3 sekunde između upita, što je oko dva upita po naručitelju. Molimo vas da nam javite je li takvo korištenje prihvatljivo ili preferirate drugi način, primjerice skupni izvoz ili isti API.

Zanima nas i pod kojim uvjetima smijemo ponovno objavljivati podatke iz registra ugovora (licenca) te kako želite da navedemo izvor.

Rado ćemo prilagoditi učestalost ili način preuzimanja vašim uvjetima. Unaprijed zahvaljujemo.

Srdačan pozdrav,

[Ime i prezime]
[Uloga u timu]
[Naziv tima / udruge]
[E-mail] · [Telefon]
Projekt: https://github.com/1212mauro/moja-opcina-u-brojkama *(repozitorij je trenutno privatan; po potrebi uklonite ovaj redak)*
