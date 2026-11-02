# Data spot-check (task G3)

**2 November 2026.** Ten figures on each pilot's page, 50 in all, compared with the source file each came from: total revenue and expenditure, the largest revenue type and spending function, population, spending per resident, the latest contract, the latest month of payments, twelve months of payments, and the largest recipient.

**Result: 50 of 50 agree to the cent.**

## How

`scripts/spot_check.py` reads the raw files in `data/raw/` with plain openpyxl, fastexcel and json, and none of the pipeline's parsers. It compares them with the exported pages (`web/public/data/m/<slug>.json`). A parsing or summing mistake in the pipeline would show up as a mismatch.

```
pipeline/.venv/Scripts/python -X utf8 scripts/spot_check.py
```

It exits with an error if any figure differs, so it can be run again after every data change.

## What the check found

- **Fixed: a municipality was shown as its own largest recipient.** Jalžabet's page said "Općina Jalžabet received the most money (1,286,424 €)", and Sveti Ilija's said the same of itself. Kipos lists every payment it does not itemise under the payer's own name and OIB: transfers to its own kindergarten (account 367), donations (381), loan repayments (542). The municipality did not receive that money; it paid it out to recipients it does not name. These payments still count in the monthly totals, but are no longer listed among recipients (`export.payments_section`, test `test_the_unit_paying_itself_is_not_a_recipient`). The largest real recipients are now GKP PRE-KOM d.o.o. (Jalžabet) and PORTAL d.o.o. (Sveti Ilija).
- **Recipients are grouped by OIB, not by name, and that is right.** Breznički Hum writes one supplier three ways in different months ("Čukelj, vl. Mario Čukelj", "Čukelj, obrt za iskope i prijevoz", "Čukelj"); its total of 124,717.61 € is the sum of all rows with OIB 87369724624. A separate company of the same owner (Čukelj iskopi i prijevoz d.o.o., another OIB) is correctly kept apart.
- **For the open privacy question:** that top recipient is a sole trader (obrt) named after its owner. It is shown by name under the current rule for registered businesses, which is one of the two cases still waiting for a decision.
- **Breznički Hum's own monthly totals** ("UKUPNO ZA RUJAN 2026.") were used as the source of its payment figures, so those two figures check the pipeline against the municipality's own arithmetic, not against our reading of its rows.

## Figures

| Pilot | Brojka | Na stranici | U izvoru | Izvor | |
| --- | --- | --- | --- | --- | --- |
| lepoglava | Prihodi 2025 (X067) | 5.734.680,11 € | 5.734.680,11 € | county.xlsx › GRAD LEPOGLAVA › „Ostvareno u 2025” | ✅ |
| lepoglava | Rashodi 2025 (Y034) | 5.575.007,75 € | 5.575.007,75 € | county.xlsx › GRAD LEPOGLAVA › „Ostvareno u 2025” | ✅ |
| lepoglava | Najveći prihod: 61 Prihodi od poreza | 3.478.227,86 € | 3.478.227,86 € | county.xlsx › GRAD LEPOGLAVA › „Ostvareno u 2025” | ✅ |
| lepoglava | Najveća funkcija: 06 Usluge unapređenja stanovanja  | 1.531.870,01 € | 1.531.870,01 € | county.xlsx › GRAD LEPOGLAVA › „Ostvareno u 2025” | ✅ |
| lepoglava | Stanovnika 2025. | 6.653 | 6.653 | estimates.xlsx › Tab-2. › Lepoglava | ✅ |
| lepoglava | Rashodi po stanovniku | 837,97 € | 837,97 € | Y034 / procjena stanovništva | ✅ |
| lepoglava | Zadnji ugovor (2026-01-14, RSM Croatia d.o.o.) | 19.500,00 € | 19.500,00 € | contracts_municipal/79368224789/grad-lepoglava-registar-sklopljenih-ugovora-za-2025-godinu.xlsx; contract URL, supplier OIB agree | ✅ |
| lepoglava | Isplate 2026-10 | 303.387,35 € | 303.387,35 € | payments/02291/<godina>.json (data), svi retci tog mjeseca | ✅ |
| lepoglava | Isplate, 12 mjeseci | 5.365.807,16 € | 5.365.807,16 € | payments/02291/<godina>.json (data), svi retci 2025-11 – 2026-10 | ✅ |
| lepoglava | Najveći primatelj: Dječji vrtić "Lepoglava" | 1.036.284,42 € | 1.036.284,42 € | payments/02291/<godina>.json (data), retci s OIB-om 54264947514 | ✅ |
| marusevec | Prihodi 2025 (X067) | 3.927.804,70 € | 3.927.804,70 € | county.xlsx › OPĆINA MARUŠEVEC › „Ostvareno u 2025” | ✅ |
| marusevec | Rashodi 2025 (Y034) | 3.924.474,70 € | 3.924.474,70 € | county.xlsx › OPĆINA MARUŠEVEC › „Ostvareno u 2025” | ✅ |
| marusevec | Najveći prihod: 61 Prihodi od poreza | 2.329.760,98 € | 2.329.760,98 € | county.xlsx › OPĆINA MARUŠEVEC › „Ostvareno u 2025” | ✅ |
| marusevec | Najveća funkcija: 04 Ekonomski poslovi | 1.330.449,83 € | 1.330.449,83 € | county.xlsx › OPĆINA MARUŠEVEC › „Ostvareno u 2025” | ✅ |
| marusevec | Stanovnika 2025. | 5.539 | 5.539 | estimates.xlsx › Tab-2. › Maruševec | ✅ |
| marusevec | Rashodi po stanovniku | 708,52 € | 708,52 € | Y034 / procjena stanovništva | ✅ |
| marusevec | Zadnji ugovor (2024-01-22, NIGRAD) | 134.569,60 € | 134.569,60 € | contracts_eojn_legacy/26670454549.xlsx › RPT_Ugovor; supplier OIB, date 22. 01. 2024. agree; amount „134.569,60 EUR” | ✅ |
| marusevec | Isplate 2026-09 | 392.174,07 € | 392.174,07 € | payments/02607/payments.json (tableData), svi retci tog mjeseca | ✅ |
| marusevec | Isplate, 12 mjeseci | 5.061.394,98 € | 5.061.394,98 € | payments/02607/payments.json (tableData), svi retci 2025-10 – 2026-09 | ✅ |
| marusevec | Najveći primatelj: DJEČJI VRTIĆ ČAROLIJA | 681.250,00 € | 681.250,00 € | payments/02607/payments.json (tableData), retci s OIB-om 37843971638 | ✅ |
| sveti-ilija | Prihodi 2025 (X067) | 3.098.697,47 € | 3.098.697,47 € | county.xlsx › OPĆINA SVETI ILIJA › „Ostvareno u 2025” | ✅ |
| sveti-ilija | Rashodi 2025 (Y034) | 3.604.330,16 € | 3.604.330,16 € | county.xlsx › OPĆINA SVETI ILIJA › „Ostvareno u 2025” | ✅ |
| sveti-ilija | Najveći prihod: 61 Prihodi od poreza | 2.137.970,20 € | 2.137.970,20 € | county.xlsx › OPĆINA SVETI ILIJA › „Ostvareno u 2025” | ✅ |
| sveti-ilija | Najveća funkcija: 06 Usluge unapređenja stanovanja  | 1.290.674,51 € | 1.290.674,51 € | county.xlsx › OPĆINA SVETI ILIJA › „Ostvareno u 2025” | ✅ |
| sveti-ilija | Stanovnika 2025. | 3.181 | 3.181 | estimates.xlsx › Tab-2. › Sveti Ilija | ✅ |
| sveti-ilija | Rashodi po stanovniku | 1.133,08 € | 1.133,08 € | Y034 / procjena stanovništva | ✅ |
| sveti-ilija | Zadnji ugovor (2023-12-12, PRE-CON d.o.o.) | 7.800,00 € | 7.800,00 € | contracts_eojn_legacy/10443118219.xlsx › RPT_Ugovor; supplier OIB, date 12. 12. 2023. agree; amount „7.800,00 EUR” | ✅ |
| sveti-ilija | Isplate 2026-09 | 176.278,04 € | 176.278,04 € | payments/04383/payments.json (tableData), svi retci tog mjeseca | ✅ |
| sveti-ilija | Isplate, 12 mjeseci | 3.205.550,71 € | 3.205.550,71 € | payments/04383/payments.json (tableData), svi retci 2025-10 – 2026-09 | ✅ |
| sveti-ilija | Najveći primatelj: PORTAL D.O.O. | 326.353,15 € | 326.353,15 € | payments/04383/payments.json (tableData), retci s OIB-om 16576658887 | ✅ |
| jalzabet | Prihodi 2025 (X067) | 3.770.803,80 € | 3.770.803,80 € | county.xlsx › OPĆINA JALŽABET › „Ostvareno u 2025” | ✅ |
| jalzabet | Rashodi 2025 (Y034) | 5.562.526,32 € | 5.562.526,32 € | county.xlsx › OPĆINA JALŽABET › „Ostvareno u 2025” | ✅ |
| jalzabet | Najveći prihod: 63 Pomoći iz inozemstva i od subj | 1.784.177,84 € | 1.784.177,84 € | county.xlsx › OPĆINA JALŽABET › „Ostvareno u 2025” | ✅ |
| jalzabet | Najveća funkcija: 09 Obrazovanje | 2.310.710,28 € | 2.310.710,28 € | county.xlsx › OPĆINA JALŽABET › „Ostvareno u 2025” | ✅ |
| jalzabet | Stanovnika 2025. | 3.206 | 3.206 | estimates.xlsx › Tab-2. › Jalžabet | ✅ |
| jalzabet | Rashodi po stanovniku | 1.735,04 € | 1.735,04 € | Y034 / procjena stanovništva | ✅ |
| jalzabet | Zadnji ugovor (2025-04-10, LIBER MEDIA d.o.o.) | 169.499,09 € | 169.499,09 € | contracts_ted/notices.jsonl › 254452-2025; date, supplier OIB agree | ✅ |
| jalzabet | Isplate 2026-09 | 266.812,55 € | 266.812,55 € | payments/01651/payments.json (tableData), svi retci tog mjeseca | ✅ |
| jalzabet | Isplate, 11 mjeseci | 3.049.327,34 € | 3.049.327,34 € | payments/01651/payments.json (tableData), svi retci 2025-10 – 2026-09 | ✅ |
| jalzabet | Najveći primatelj: GKP PRE-KOM D.O.O. | 161.870,77 € | 161.870,77 € | payments/01651/payments.json (tableData), retci s OIB-om 15704341739 | ✅ |
| breznicki-hum | Prihodi 2025 (X067) | 995.306,26 € | 995.306,26 € | county.xlsx › OPĆINA BREZNIČKI HUM › „Ostvareno u 2025” | ✅ |
| breznicki-hum | Rashodi 2025 (Y034) | 1.189.036,24 € | 1.189.036,24 € | county.xlsx › OPĆINA BREZNIČKI HUM › „Ostvareno u 2025” | ✅ |
| breznicki-hum | Najveći prihod: 61 Prihodi od poreza | 602.829,44 € | 602.829,44 € | county.xlsx › OPĆINA BREZNIČKI HUM › „Ostvareno u 2025” | ✅ |
| breznicki-hum | Najveća funkcija: 04 Ekonomski poslovi | 528.187,67 € | 528.187,67 € | county.xlsx › OPĆINA BREZNIČKI HUM › „Ostvareno u 2025” | ✅ |
| breznicki-hum | Stanovnika 2025. | 1.102 | 1.102 | estimates.xlsx › Tab-2. › Breznički Hum | ✅ |
| breznicki-hum | Rashodi po stanovniku | 1.078,98 € | 1.078,98 € | Y034 / procjena stanovništva | ✅ |
| breznicki-hum | Zadnji ugovor (2023-09-14, NISKOGRADNJA HUĐEK, vl) | 62.120,20 € | 62.120,20 € | contracts_eojn_legacy/35774913576.xlsx › RPT_Ugovor; supplier OIB, date 14. 09. 2023. agree; amount „62.120,20 EUR” | ✅ |
| breznicki-hum | Isplate 2026-09 | 79.132,34 € | 79.132,34 € | Informacije_o_trosenju_sredstava_09-26.ods › „UKUPNO” (zbroj koji objavljuje općina) | ✅ |
| breznicki-hum | Isplate, 12 mjeseci | 894.037,61 € | 894.037,61 € | zbroj „UKUPNO” redaka mjesečnih datoteka | ✅ |
| breznicki-hum | Najveći primatelj: Čukelj, vl. Mario Čukelj | 124.717,61 € | 124.717,61 € | mjesečne .ods datoteke, retci s OIB-om 87369724624 (i retci nastavka) | ✅ |
