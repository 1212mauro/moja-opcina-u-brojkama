# Zahtjev: automatizirani pristup podacima o isplatama (Otvoreni grad / iTransparentnost)

> **Draft, not sent.** Asks Ludbreg and Ivanec (and through them their platform provider, Libusoft Cicom d.o.o.) to allow the project's nightly job to read their payment disclosures from `api.otvorenigrad.hr`, which currently answers 403 to GitHub's servers. Fill in the `[…]` fields before sending. Libusoft Cicom publishes no contact address that could be verified, so the cities are asked to forward it.

**Za:** grad@ludbreg.hr, grad@ivanec.hr
**Predmet:** Zahtjev za automatizirani pristup podacima o trošenju sredstava (Otvoreni grad – iTransparentnost)

---

Poštovani,

obraćamo vam se kao [naziv tima / udruge] koji u sklopu [naziv datathona] razvija otvorenu, nekomercijalnu web-aplikaciju **„Moja općina u brojkama”**. Aplikacija građanima na jednoj stranici, jednostavnim jezikom, prikazuje proračun, javnu nabavu, isplate i javne usluge njihovog grada ili općine te ih uspoređuje sa sličnim jedinicama u istoj županiji. Grad Ludbreg i Grad Ivanec dvije su od pet pilot-jedinica u Varaždinskoj županiji. Izvorni kod objavljujemo pod licencom EUPL-1.2.

Podatke o isplatama koje objavljujete prema Naputku o okvirnom sadržaju te minimalnim uvjetima pretraživanja i preuzimanja informacija o trošenju sredstava (NN 59/23) preuzimamo s vaše platforme iTransparentnost, putem istog sučelja koje koristi vaša javna stranica:

- adresa: `https://api.otvorenigrad.hr/itransparentnost/isplate` (format CSV, zaglavlje `LC-Tenant: grad-ludbreg` odnosno `grad-ivanec`);
- učestalost: jednom noćno (oko 03:30 UTC), samo tekući i prethodni mjesec, dakle **dva upita po gradu na noć**, uz stanku između upita;
- identifikacija: svaki upit nosi User-Agent `moja-opcina-u-brojkama/0.1 (+https://github.com/1212mauro/moja-opcina-u-brojkama)`.

Isplate fizičkim osobama prikazujemo isključivo onako kako ih vi objavljujete, kao zbirne kategorije, bez imena. Ne objavljujemo ništa što već nije javno objavljeno na vašoj stranici.

S računala u Hrvatskoj sučelje radi bez problema, ali **naš noćni posao pokreće se na GitHub Actions (Microsoft Azure) i na svaki upit dobiva odgovor 403 Forbidden**. Pretpostavljamo da platforma namjerno blokira promet iz podatkovnih centara. To poštujemo i ne želimo zaobilaziti.

Stoga vas molimo:

1. **Odobreni način automatiziranog pristupa**, ako je moguć: API ključ ili token koji bismo slali u zaglavlju, ili drugi način koji vaš dobavljač, Libusoft Cicom d.o.o., preporučuje. Dopuštanje pristupa po IP adresi teško je izvedivo jer GitHub koristi vrlo velike i promjenjive raspone adresa. Ako je lakše, molimo da ovaj upit proslijedite Libusoft Cicomu ili nam javite kontakt osobe kod njih.
2. Ako to nije moguće, bi li bilo prihvatljivo objavljivati iste podatke i kao otvoreni skup podataka na portalu data.gov.hr? Grad Novi Marof, koji koristi istu platformu, to već radi („iTransparentnost – isplate iz proračuna Grada Novog Marofa”), kao i Općina Breznica.
3. Pod kojom licencom smijemo ponovno koristiti ove podatke (npr. Otvorena dozvola Republike Hrvatske) i kako želite da navedemo izvor.

Rado ćemo prilagoditi učestalost ili način preuzimanja vašim uvjetima. Unaprijed zahvaljujemo na pomoći.

Srdačan pozdrav,

[Ime i prezime]
[Uloga u timu]
[Naziv tima / udruge]
[E-mail] · [Telefon]
Projekt: https://github.com/1212mauro/moja-opcina-u-brojkama *(repozitorij je trenutno privatan; po potrebi pošaljite GitHub korisničko ime za pristup ili ga uklonite iz poruke)*
