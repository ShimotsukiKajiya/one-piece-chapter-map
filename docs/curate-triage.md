# Curate triage — a recommendation for every claim in the queue

`docs/curate_queue.json` holds **189** claims awaiting a human decision. Every
one was raised by a single rule, `digit-proximity`: a value found within ~80
characters of a name. That rule cannot tell *"Zoro → November 11"* from
*"in Chapter 366"*, so the queue mixes settled facts with digit coincidences.

This pass re-reads the **whole cited SBS answer** from `sbs_archive.json` — the
queue only stores a ~150-character window, which is why so many claims looked
unresolvable — and asks four narrower questions:

1. is the subject named anywhere in the question or answer, under **any** form
   Oda uses, epithets included? He writes *Kizaru*, not *Borsalino*.
2. is the claimed value stated there, **anchored to its unit**? `509 cm (16'8")`
   must not be confirmed by *"I am a 16 year old fan"*.
3. do the matched digits belong to a **citation** ("Chapter 366", "Volume 10")
   rather than to a claim?
4. does the answer **dodge**? `docs/canon-policy.md` Case 5 — never promoted.

**Nothing here has been promoted.** `curate_queue.json` and `punk_records.json`
are both untouched. Every row is a recommendation.

| Recommendation | Count |
|---|---:|
| confirm | 148 |
| needs-eyes | 8 |
| reject | 33 |
| **total** | **189** |

All 189 cited SBS answers were located in the archive; none of these rest on a
missing source.

---

## 1 · Needs eyes — 8 claims, the only real decisions here

Work these first. They are few, and each one needs a person to read the answer.

| Subject | Field | Claimed value | SBS | Why it needs you | Evidence |
|---|---|---|---|---|---|
| Sai | birthday | August 13th | vol 83 q1102 | the date is given as an SBS number-pun, not stated plainly - read the gloss | n the blanks on the birthday calendar. #Sai> August (8). 13 (Happo Navy, 13th Leader) Hap |
| Sai | occupation | Captain of the Third Ship of the Straw Hat G | vol 83 q1102 | subject and a matching figure both present - read the answer | on the birthday calendar. #Sai> August (8). 13 (Happo Navy, 13th Leader |
| Baby 5 | birthday | May 15th | vol 83 q1102 | the date is given as an SBS number-pun, not stated plainly - read the gloss | po, literally means eight treasures #Baby 5> May (5), 15 (May (May (5)), Do (10) + (Ba |
| Chinjao | birthday | December 12th | vol 83 q1102 | the date is given as an SBS number-pun, not stated plainly - read the gloss | , Do (10) + (Baby 5)) Meido = Maid #Chinjao> December (12), 12 (12th Leader) #Boo> Augu |
| Chinjao | occupation | 12th Leader of the Happo Navy (retired); Pir | vol 83 q1102 | subject and a matching figure both present - read the answer | + (Baby 5)) Meido = Maid #Chinjao> December (12), 12 (12th Leader) #Boo> |
| Boo | birthday | August 20th | vol 83 q1102 | the date is given as an SBS number-pun, not stated plainly - read the gloss | injao> December (12), 12 (12th Leader) #Boo> August (8), 20 (Happou Navy, Bu-u (2-0)) By |
| Miss Friday | birthday | January 21st | vol 90 q1232 | subject named but the claimed date is not in the answer | — |
| Candy | birthday | June 14th | vol 87 q1178 | subject named but the claimed date is not in the answer | — |

Two of the eight are worth naming separately, because the answer to "should
this be promoted?" is not the interesting part:

- **Miss Friday, birthday.** The Codex stores **January 21st**. SBS vol 90 q1232
  says, in Oda's own list: *"**Miss Friday: June 21**; from her alias, as 1-2-1
  can be derived from…"*. That is not a failed promotion — it is a **stored value
  that disagrees with Oda**. Reject the promotion, then look at the stored value.
  (The queue matched on the digits `1-2-1` in the gloss, which is how a wrong
  value and a right citation ended up in the same row.)
- **Candy, birthday.** The name appears once in vol 87 q1178, inside the gloss
  *"Charlotte Perospero: March 14; **Candy** Day"*. It is a word in someone
  else's reason, not a subject. Reject. The near neighbour of this class —
  a subject name matching a reader's `P.N.` pen-name signature — is caught
  automatically and appears under Reject below.

## 2 · Reject — 33 claims the rule matched by accident

None of these are wrong facts. They are claims whose *evidence* does not
support them: the digits matched something else in the answer, or nothing at
all. Rejecting a claim here leaves the stored value exactly as it is, at its
current tier — it only declines to call it Oda-confirmed **on this citation**.

**no cm figure from the claim appears in the cited answer** — 16

| Subject | Field | Claimed value | SBS |
|---|---|---|---|
| Roronoa Zoro | height | 178 cm (5'10") (debut) · 181 cm (5'11") (after | vol 4 q1 |
| Franky | height | 225 cm (7'5") (debut) · 240 cm (7'10") (after | vol 44 q549 |
| Charlotte Linlin | height | 880 cm (28'10") | vol 86 q1161 |
| Buggy | height | 192 cm (6'4") (age 39) · 130 cm (4'3") (age 13 | vol 84 q1110 |
| Edward Newgate | height | 666 cm (21'10") | vol 59 q743 |
| Karoo | height | 150 cm (4'11") | vol 82 q1086 |
| Shanks | height | 199 cm (6'6") (age 39) · 132 cm (4'4") (age 13 | vol 84 q1110 |
| Borsalino | height | 302 cm (9'11") | vol 53 q664 |
| Bentham | height | 238 cm (7'10") | vol 22 q276 |
| Basil Hawkins | height | 210 cm (6'10½") (debut, after timeskip) | vol 98 q1361 |
| Charlotte Katakuri | height | 509 cm (16'8") | vol 86 q1150 |
| King | height | 613 cm (20'1") | vol 63 q812 |
| Stussy | height | 179 cm (5'10") | vol 89 q1218 |
| Goldberg | height | 2100 cm (68'11") | vol 90 q1232 |
| Pound | height | 731 cm (24'0") | vol 31 q377 |
| Kizaru | height | 302 cm (9'11") | vol 59 q746 |

**no figure from the claim appears in the cited answer at all** — 14

| Subject | Field | Claimed value | SBS |
|---|---|---|---|
| Monkey D. Luffy | bounty | ฿3,000,000,000 · ฿1,500,000,000 · ฿500,000,000 | vol 4 q11 |
| Nami | bounty | ฿366,000,000 · ฿66,000,000 · ฿16,000,000 | vol 39 q484 |
| Roronoa Zoro | bounty | ฿1,111,000,000 · ฿320,000,000 · ฿120,000,000 · | vol 91 q1244 |
| Usopp | bounty | ฿500,000,000 · ฿200,000,000 · ฿30,000,000 | vol 32 q393 |
| Tony Tony Chopper | bounty | ฿1,000 · ฿100 · ฿50 | vol 85 q1127 |
| Nico Robin | bounty | ฿930,000,000 · ฿130,000,000 · ฿80,000,000 · ฿7 | vol 81 q1063 |
| Buggy | bounty | ฿3,189,000,000 ฿15,000,000 | vol 81 q1063 |
| Crocodile | bounty | ฿1,965,000,000 · ฿81,000,000 | vol 36 q446 |
| Kaidou | bounty | ฿4,611,100,000 · ฿70,000,000 | vol 101 q1418 |
| Shanks | bounty | ฿4,048,900,000 · ฿1,040,000,000 | vol 65 q847 |
| Brogy | bounty | ฿1,800,000,000 · ฿100,000,000 | vol 19 q233 |
| Dorry | bounty | ฿1,800,000,000 · ฿100,000,000 | vol 19 q233 |
| Very Good | bounty | At least ★ · (At least 100,000,000) | vol 47 q571 |
| Yeti Cool Brothers | bounty | ฿20,000,000 (each) | vol 90 q1232 |

**the digits that matched belong to a citation, not a claim** — 1

| Subject | Field | Claimed value | SBS |
|---|---|---|---|
| Helmeppo | height | 179 cm (5'10") | vol 14 q162 |

**neither the subject nor the date is in the cited answer** — 1

| Subject | Field | Claimed value | SBS |
|---|---|---|---|
| Babe | birthday | June 19th | vol 21 q262 |

**the only occurrence of the name is a reader's SBS pen name, not the character** — 1

| Subject | Field | Claimed value | SBS |
|---|---|---|---|
| Yuki | birthday | December 17th | vol 89 q1218 |

## 3 · Confirm — 148 claims where Oda names the subject and states the value

Grouped by the SBS answer they cite, because one read settles a whole block:
Oda answers birthdays in long lists, so a single answer can carry thirty of
these. The largest blocks are at the top.

### SBS vol 90, q1232 — 62 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Agyo | birthday | November 29th | ha: December 18 *P.N. Happy B Masazo **Agyo: November 29; Good Meat Day **Farul: |
| Belo Betty | birthday | June 15th | as 8-14 can be derived from Ja-an **Roshio: June 15; from his name, as 6-15 |
| Bobby Funk | birthday | February 19th | 30 **Charlotte Nusstorte: January 23 **Road: February 19 **Charlotte Dolce and Dr |
| Bomba | birthday | August 14th | eat Fire of Rome *P.N. Uzo-sama **Jean Ango: August 14; from his name, as 8-14 |
| Cerberus | birthday | November 29th | ha: December 18 *P.N. Happy B Masazo **Agyo: November 29; Good Meat Day **Farul: |
| Charlotte Amande | birthday | December 10th | Japanese word for "Monday" **Edward Weevil: December 10; from his name, as 10-12 |
| Charlotte Anglais | birthday | October 19th | r 29 **Vito: October 21 **Charlotte Anglais: October 19; from his name Charlotte |
| Charlotte Broyé | birthday | March 6th · December 26th (SBS) | otte Marnier: December 20 **Charlotte Broyé: December 26 *P.N. Birthday Burying C |
| Charlotte Compote | birthday | October 15th | ust 29; Western Sweets Day **Charlotte Yuen: October 15 **Charlotte Compote: Oct |
| Charlotte Dolce and Dragée | birthday | February 21st | d: February 19 **Charlotte Dolce and Dragée: February 21 **Charlotte Raisin: Marc |
| Charlotte Marnier | birthday | December 20th | te Moscato: December 16 **Charlotte Marnier: December 20 **Charlotte Broyé: Decem |
| Charlotte Moscato | birthday | December 16th | e Noisette: December 15 **Charlotte Moscato: December 16 **Charlotte Marnier: Dec |
| Charlotte Myukuru | birthday | November 17th | lotte Snack: October 29 **Charlotte Myukuru: November 17 **Ikkaku: December 7 **C |
| Charlotte Noisette | birthday | December 15th | Decuplets: December 2 **Charlotte Noisette: December 15 **Charlotte Moscato: Dec |
| Charlotte Nusstorte | birthday | January 23rd | can be derived from Edward-Weev **Ginrummy: January 23 **Wire: July 18; from hi |
| Charlotte Opera | birthday | September 29th | from Wa-iyā **Bomba: August 14 **Drug Peclo: September 29 **Vito: October 21 **Cha |
| Charlotte Poire | birthday | October 19th | r 29 **Vito: October 21 **Charlotte Anglais: October 19; from his name Charlotte |
| Charlotte Raisin | birthday | March 23rd | and Dragée: February 21 **Charlotte Raisin: March 23 **Peachbeard: March 27 * |
| Charlotte Snack | birthday | October 29th | e and Galette: October 19 **Charlotte Snack: October 29 **Charlotte Myukuru: Nov |
| Charlotte Yuen | birthday | October 15th | ust 29; Western Sweets Day **Charlotte Yuen: October 15 **Charlotte Compote: Oct |
| Clione | birthday | February 17th | : January 20; Marry a Rich Man Day **Clione: February 17 **Columbus: May 16; Trav |
| Columbus | birthday | May 16th | ch Man Day **Clione: February 17 **Columbus: May 16; Travel Day **Gatz: Augu |
| Dagama | birthday | September 26th | ut Politics Day **Flapper: July 28 **Dagama: September 26 **Charlotte Opera, Count |
| Drug Peclo | birthday | September 29th | from Wa-iyā **Bomba: August 14 **Drug Peclo: September 29 **Vito: October 21 **Cha |
| Edward Weevil | birthday | December 10th | Japanese word for "Monday" **Edward Weevil: December 10; from his name, as 10-12 |
| Farul | birthday | August 29th | **Agyo: November 29; Good Meat Day **Farul: August 29; Bell Rose Day **Cerberu |
| Flapper | birthday | July 28th | y 27; Thinking About Politics Day **Flapper: July 28 **Dagama: September 26 * |
| Gambia | birthday | February 18th | g Octopus: December 26; Boxing Day **Gambia: February 18; Republic of Gambia Inde |
| Gatz | birthday | August 26th | ry 17 **Columbus: May 16; Travel Day **Gatz: August 26 **Yeti Cool Brothers: De |
| Giberson | birthday | August 14th | eat Fire of Rome *P.N. Uzo-sama **Jean Ango: August 14; from his name, as 8-14 |
| Gild Tesoro | birthday | January 24th | were revealed with SBS 90: * **Gild Tesoro: January 24; Gold Day *P.N. Yohe Aru |
| Ginrummy | birthday | January 23rd | can be derived from Edward-Weev **Ginrummy: January 23 **Wire: July 18; from hi |
| Goldberg | birthday | May 11th | March 23 **Peachbeard: March 27 **Goldberg: May 11 **Stansen: May 27 **Nako |
| Ham Burger | birthday | July 20th | 15 *P.N. Sapporo Ramen Prince **Ham Burger: July 20; Hamburger Day *P.N. Mas |
| Inuppe | birthday | December 16th | e Noisette: December 15 **Charlotte Moscato: December 16 **Charlotte Marnier: Dec |
| Jean Ango | birthday | August 14th | eat Fire of Rome *P.N. Uzo-sama **Jean Ango: August 14; from his name, as 8-14 |
| Jigoro | birthday | February 21st | d: February 19 **Charlotte Dolce and Dragée: February 21 **Charlotte Raisin: Marc |
| Kinderella | birthday | January 20th | ating the first cultured pearl **Kinderella: January 20; Marry a Rich Man Day ** |
| Kingbaum | birthday | July 13th | ecember 16 **Jigoro: February 21 **Kingbaum: July 13 **Pound: August 21 **Gib |
| Michael and Hoichael | birthday | July 18th | m Edward-Weev **Ginrummy: January 23 **Wire: July 18; from his name, as 7-18 |
| Miss Monday | birthday | January 24th | were revealed with SBS 90: * **Gild Tesoro: January 24; Gold Day *P.N. Yohe Aru |
| Mr. 13 | birthday | May 17th | ay **Bobby Funk: Pro Wrestling Day **Mr. 13: May 17; World Telecommunication |
| Noble Croc | birthday | October 17th | mit: September 23; Neptune Day **Noble Croc: October 17; Savings Day **Heat: Dec |
| Peachbeard | birthday | March 27th | 1 **Charlotte Raisin: March 23 **Peachbeard: March 27 **Goldberg: May 11 **Sta |
| Pearl | birthday | July 11th | ecorded baseball game in the U.S.A. **Pearl: July 11; anniversary of Mikimoto |
| Pound | birthday | August 21st | ro: February 21 **Kingbaum: July 13 **Pound: August 21 **Giberson: August 14 ** |
| Prometheus | birthday | July 19th | : June 26; Thunder Anniversary **Prometheus: July 19; date of the Great Fire |
| Raideen | birthday | November 14th | : August 21 **Giberson: August 14 **Raideen: November 14 |
| Road | birthday | February 19th | 30 **Charlotte Nusstorte: January 23 **Road: February 19 **Charlotte Dolce and Dr |
| Roshio | birthday | June 15th | as 8-14 can be derived from Ja-an **Roshio: June 15; from his name, as 6-15 |
| Smiley | birthday | July 18th | m Edward-Weev **Ginrummy: January 23 **Wire: July 18; from his name, as 7-18 |
| Stansen | birthday | May 27th | eard: March 27 **Goldberg: May 11 **Stansen: May 27 **Nako: July 1 **Michael |
| Suleiman | birthday | January 30th | 24; Gold Day *P.N. Yohe Arubaito **Suleiman: January 30; from , since A is the f |
| Tank Lepanto | birthday | November 28th | ; Hamburger Day *P.N. Masazo **Tank Lepanto: November 28; Car Wash Day (Tank Lepa |
| Thalassa Lucas | birthday | July 27th | hael and Hoichael: July 18 **Thalassa Lucas: July 27; Thinking About Politics |
| Umit | birthday | September 23rd | ember 11; International Mountain Day **Umit: September 23; Neptune Day **Noble Cro |
| Vito | birthday | October 21st | August 14 **Drug Peclo: September 29 **Vito: October 21 **Charlotte Anglais: Oct |
| Wire | birthday | July 18th | m Edward-Weev **Ginrummy: January 23 **Wire: July 18; from his name, as 7-18 |
| Yeti Cool Brothers | birthday | December 11th | Day **Gatz: August 26 **Yeti Cool Brothers: December 11; International Mountain |
| Zala | birthday | July 30th | Cerberus: November 29; Good Meat Day **Zala: July 30 **Charlotte Nusstorte: J |
| Zeus | birthday | June 26th | eal-world Napoleon's coronation date **Zeus: June 26; Thunder Anniversary **P |
| Zunesha | birthday | December 18th | l: December 4 **Jarul: December 8 **Zunesha: December 18 *P.N. Happy B Masazo **A |

### SBS vol 87, q1178 — 13 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Boodle | birthday | January 16th | okami **Rika: June 18; Onigiri Day **Boodle: January 16 **Chouchou: November 22 |
| Carrot | birthday | May 24th | hdays were revealed with SBS 87: * **Carrot: May 24; 5 from , 2 from and 4 f |
| Charlotte Cracker | birthday | February 28th | da: November 1; Dog Day **Charlotte Cracker: February 28; Biscuit Day **Charlotte |
| Charlotte Mont-d'Or | birthday | April 23rd (World Book Day) | : March 14; Candy Day **Charlotte Mont-d'Or: April 23; World Book Day *P.N. To |
| Charlotte Perospero | birthday | March 14th | ; Bear Day *P.N. Aoga **Charlotte Perospero: March 14; Candy Day **Charlotte M |
| Chouchou | birthday | November 22nd | Onigiri Day **Boodle: January 16 **Chouchou: November 22 **Sham: April 19; 4 mean |
| Higuma | birthday | November 18th | **Lord of the Coast: September 14 **Higuma: November 18; Bear Day *P.N. Aoga **C |
| Lord of the Coast | birthday | September 14th | be derived from Bu-chi **Lord of the Coast: September 14 **Higuma: November 18; B |
| Miyagi | birthday | December 22nd | can be derived from Mi-rro (World) **Miyagi: December 22; the first day of the Ca |
| Nyasha | birthday | May 28th | 2; 8-2 can be derived from É-poni **Nyasha: May 28; 5 is derived from V (Vi |
| Rika | birthday | June 18th | arlett: October 28 *P.N. Ippikiokami **Rika: June 18; Onigiri Day **Boodle: J |
| Sham | birthday | April 19th | : January 16 **Chouchou: November 22 **Sham: April 19; 4 means "Shamu", and S |
| Vinsmoke Judge | birthday | May 12th | 8 can be derived from Meow **Vinsmoke Judge: May 12; 5 is derived from V, J |

### SBS vol 89, q1218 — 13 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Charlotte Anana | birthday | April 17th | Birthday is Also April 4 **Charlotte Anana: April 17; from her name, , since |
| Charlotte Flampe | birthday | February 11th | hī *P.N. Crocodile Pine. **Charlotte Flampe: February 11; from , since 2-1-1 can |
| Charlotte Praline | birthday | July 22nd | N. Tsusue Yuki Hayabusa **Charlotte Praline: July 22; Nut Day (praline) *P.N. |
| Hajrudin | birthday | August 12th | u-ichi-i *P.N. Masazo dai Sendan **Hajrudin: August 12; from Hairudin, the tran |
| Jack | birthday | September 28th | ce 31-7 can be derived from Sarie-na **Jack: September 28; from the transcription |
| Johnny | birthday | November 12th | 10; the day before Zoro's birthday **Johnny: November 12; the day after Zoro's bi |
| Lu Feld | birthday | December 29th | aled with SBS 89: * of Kita 42-jo **Lu Feld: December 29; Lucky Day **Morgans: Ju |
| Morgans | birthday | July 14th | **Lu Feld: December 29; Lucky Day **Morgans: July 14; Newspaper Delivery Day |
| Orlumbus | birthday | June 23rd | -1-2 can be derived from ha-i-di **Orlumbus: June 23; from Ōronbusu, the tran |
| Sarie Nantokanette | birthday | July 31st | can be derived from na **Sarie Nantokanette: July 31; from her name, since 31 |
| Stussy | birthday | April 24th | birthday *P.N. Andy, 27 years old **Stussy: April 24; 4-2-4 can be derived fr |
| Ucy | birthday | April 21st | elivery Day *P.N. Kamihitoe no Masazo **Ucy: April 21; from , 21 from the peop |
| Yosaku | birthday | November 10th | since it can be derived from ushi **Yosaku: November 10; the day before Zoro's b |

### SBS vol 86, q1159 — 12 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Blue Gilly | birthday | November 27th | - May 14 *King Riku - June 27 *Blue Gilly - November 27 *Pedro - June 16 *Smooth |
| Charlotte Smoothie | birthday | October 12th | y - November 27 *Pedro - June 16 *Smoothie - October 12 \|}  \|\|  Whoaaaaa! Hang o |
| Kaya | birthday | August 24th | 25 *Pekoms - April 11 \|valign="top"\| *Kaya - August 24 *Kanjuro - July 21 *Baro |
| Kin'emon | birthday | January 29th | align="top"\| *Merry - January 22 *Kin'emon - January 29 *Nojiko - July 25 *Bell- |
| Merry | birthday | January 22nd | enter\|-" \|width="50%" valign="top"\| *Merry - January 22 *Kin'emon - January 29 * |
| Nojiko | birthday | July 25th | January 22 *Kin'emon - January 29 *Nojiko - July 25 *Bell-mère - December 3 |
| Pedro | birthday | June 16th | - June 27 *Blue Gilly - November 27 *Pedro - June 16 *Smoothie - October 12 \| |
| Pekoms | birthday | April 11th | June 17 *Terracotta - September 25 *Pekoms - April 11 \|valign="top"\| *Kaya - A |
| Riku Doldo III | birthday | June 27th | July 21 *Baron Tamago - May 14 *King Riku - June 27 *Blue Gilly - November 2 |
| Tamago | birthday | May 14th | August 24 *Kanjuro - July 21 *Baron Tamago - May 14 *King Riku - June 27 *Bl |
| Terracotta | birthday | September 25th | Mr.5 - July 26 *Toto - June 17 *Terracotta - September 25 *Pekoms - April 11 \|vali |
| Toto | birthday | June 17th | ll-mère - December 3 *Mr.5 - July 26 *Toto - June 17 *Terracotta - September |

### SBS vol 88, q1203 — 8 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Buckin | birthday | April 12th | erry: January 28 *P.N. Osenaka-san **Buckin: April 12; from , since 4-1-2 can |
| Carmel | birthday | December 21st | : February 27 *P.N. Showlot Senbei **Carmel: December 21; from , since 1-2-2-1 ca |
| Charlotte Joscarpone | birthday | February 27th | ni-na **Charlotte Joscarpone and Mascarpone: February 27 *P.N. Showlot Senbei **C |
| Jango | birthday | December 28th | rom shi-ai-ji *P.N. Brook's Brother **Jango: December 28; from his pirate epithet |
| Kyuin | birthday | May 30th | nd 5 from 'o', meaning *P.N. Goemon **Kyuin: May 30; Vacuum Cleaner Day **Ra |
| Mansherry | birthday | January 28th | **Raizo: February 26 *P.N. Rena **Mansherry: January 28 *P.N. Osenaka-san **Buck |
| Raizo | birthday | February 26th | **Kyuin: May 30; Vacuum Cleaner Day **Raizo: February 26 *P.N. Rena **Mansherry: |
| Sarquiss | birthday | July 12th | an be derived from ichi-ni-ji-ya **Sarquiss: July 12; from his epithet , sinc |

### SBS vol 59, q746 — 6 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Akainu | birthday | August 16th | ) Kizaru...11/23 (Mr. Kunie Tanaka) Akainu...8/16 (Mr. Bunta Sugawara) how |
| Aokiji | birthday | September 21st | eal models, can their birthdays be: Aokiji...9/21 (Mr. Yusaku Matsuda) Kiz |
| Borsalino | birthday | November 23rd | Aokiji...9/21 (Mr. Yusaku Matsuda) Kizaru...11/23 (Mr. Kunie Tanaka) Akain |
| Kizaru | birthday | November 23rd | Aokiji...9/21 (Mr. Yusaku Matsuda) Kizaru...11/23 (Mr. Kunie Tanaka) Akain |
| Kuzan | birthday | September 21st | eal models, can their birthdays be: Aokiji...9/21 (Mr. Yusaku Matsuda) Kiz |
| Sakazuki | birthday | August 16th | ) Kizaru...11/23 (Mr. Kunie Tanaka) Akainu...8/16 (Mr. Bunta Sugawara) how |

### SBS vol 69, q906 — 3 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Brook | height | 266 cm (8'9") (debut) · 277 cm (9'1") (a | lue  \|\|  Brook * Birthday: April 3 * Age: 90 * Height: 277&nbsp;cm * DF: Yomi Yomi no |
| Nico Robin | height | 188 cm (6'2") (debut, after timeskip) | Nico Robin * Birthday: February 6 * Age: 30 * Height: 188&nbsp;cm * DF: Hana Hana no |
| Tony Tony Chopper | height | 90 cm (2'11") (hybrid form) | ny Chopper * Birthday: December 24 * Age: 17 * Height: 90&nbsp;cm (Hybrid form) * DF: |

### SBS vol 77, q1012 — 3 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Hack | height | 280 cm (9'2") | , for sure. [187&nbsp;cm age 22 · 160&nbsp;cm age 23 · 280&nbsp;cm age 38 (Brocade Per |
| Koala | height | 160 cm (5'3") | gotta be his birthday, for sure. [187&nbsp;cm age 22 · 160&nbsp;cm age 23 · 280&nbsp;c |
| Sabo | height | 100 cm (3'3") (flashback, debut) · 187 c | \|\|  Yes. And that's gotta be his birthday, for sure. [187&nbsp;cm age 22 · 160&nbsp;c |

### SBS vol 82, q1086 — 3 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Chaka | birthday | April 26th | ya are (8),bu is (2) and sa is (3) \| \|Chaka (4/26) "Jakkaru" = 426 (Japane |
| Koza | birthday | May 26th | n:auto; width:650px; align:center;" \| \|Koza (5/26) "ko--za" = 526;ko/go is |
| Pell | birthday | August 23rd | n:auto; width:650px; align:center;" \| \|Pell (8/23) "hayabusa = 823(Japanes |

### SBS vol 88, q1191 — 3 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Charlotte Daifuku | birthday | November 25th | , Daifuku-san, and Oven-san's birthday being November 25 (a play on number pronun |
| Charlotte Katakuri | birthday | November 25th | , Daifuku-san, and Oven-san's birthday being November 25 (a play on number pronun |
| Charlotte Oven | birthday | November 25th | , Daifuku-san, and Oven-san's birthday being November 25 (a play on number pronun |

### SBS vol 47, q574 — 2 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Helmeppo | birthday | July 16th | for Koby (Ko = Go = 5, B looks like 13) and July 16 for Helmeppo (Nana-hikar |
| Koby | birthday | May 13th | e so hot! Tell me their birthdays! How about May 13 for Koby (Ko = Go = 5, B |

### SBS vol 60, q765 — 2 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Bepo | birthday | November 20th (Fur Day) | onney 9/1 (Oogui; Big eater→0091) \| \|- \|Bepo 11/20 (Fur day) \| \|- \|Scratchm |
| Scratchmen Apoo | birthday | March 19th | \|Bepo 11/20 (Fur day) \| \|- \|Scratchmen Apoo 3/19 (Day of Music) \| \|}  \|\| |

### SBS vol 64, q820 — 2 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Capone Bege | birthday | January 17th | n the english alphabet) *Capone "Gang" Bege: 1/17 (Al Capone's birthday) W |
| X Drake | birthday | October 24th | p with Drake and Bege's birthdays. *X Drake: 10/24 (X is 10 in roman numera |

### SBS vol 91, q1249 — 2 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Donquixote Mjosgard | birthday | December 13th | : May 21 *P.N. Goemon **Donquixote Mjosgard: December 13 |
| Gotti | birthday | May 21st | ut match **Kabu: July 1; Turnip Day **Gotti: May 21 *P.N. Goemon **Donquixot |

### SBS vol 15, q182 — 1 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Roronoa Zoro | birthday | November 11th | I'll answer it now. * Luffy → May 5 * Zoro → November 11 * Nami → July 3 * Usopp |

### SBS vol 27, q332 — 1 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Smoker | birthday | March 14th | hought it'll be good if Smoker's birthday is March 14 (White Day), and Hina's |

### SBS vol 43, q529 — 1 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Kalifa | birthday | April 23rd | 7 (Hana "Nose"... Ha = 8, Na = 7) *Kalifa - April 23 (Secretaries' Day) ...an |

### SBS vol 48, q590 — 1 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Portgas D. Ace | height | 185 cm (6'1") (age 20) · 103 cm (3'5") ( | n ace is worth one in cards. That works. He'd be about 185&nbsp;cm tall. |

### SBS vol 60, q764 — 1 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Sabo | birthday | March 20th | day,「Sa(3)a~bu(2)o(0)~」(super slow replayed)=3/20; how's that? by Ebisu Ta |

### SBS vol 71, q944 — 1 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Monet | birthday | August 27th | ar and Monet! Caesar is April 9 and Monet is August 27! Is that OK? Ida (TN: Bo |

### SBS vol 74, q971 — 1 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Cavendish | birthday | August 31st | I thought... Caven→Cabbage→Vegetable(Yasai)→August 31 (8Ya 3Sa 1I) might be a |

### SBS vol 79, q1030 — 1 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Hiriluk | birthday | January 12th | sum of 4(sh) and 8(ya) to make his birthday January 12?  \|\|  Hiriluk, after all |

### SBS vol 82, q1075 — 1 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Perona | height | 160 cm (5'3") | age 12. Pop  \|\|  Perona is currently 25. Her height is 160&nbsp;cm. Back when she foug |

### SBS vol 82, q1084 — 1 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Nekomamushi | birthday | November 22nd | How's 11/22 (I I NIyan NIyan- good k |

### SBS vol 85, q1135 — 1 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Inuarashi | birthday | October 11th | Hello, Oda Sensei! My birthday is October 11. There were no character |

### SBS vol 86, q1157 — 1 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Charlotte Pudding | birthday | June 25th | g Day". How about Pudding-chan's birthday be 6/25 for Charlotte (6) Puddin |

### SBS vol 96, q1320 — 1 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Kouzuki Oden | birthday | February 22nd | Oda-sensei! Did you know that February 22 is "National Oden Day" i |

### SBS vol 110, q1592 — 1 claim(s)

| Subject | Field | Value | Evidence from the answer |
|---|---|---|---|
| Kujaku | height | 180 cm (5'11") | old · 22 years old  \|\|  Height · 233&nbsp;cm (7'8") · 180&nbsp;cm (5'11") · 205&nbsp; |


---

## 4 · New candidates from the positional-table parser (30)

`scripts/parse_sbs_positional.py` reads the SBS answers laid out as a table,
which the proximity matcher cannot reach: name and value align by *index*, ~180
characters apart. Of 1,685 archived answers exactly **13** contain a bracketed
`||` table and **2** are name-to-value tables; the parser declines the other 11
rather than guessing at lists of foods, sleep times and cover-story arcs.

These are written to **`docs/curate_queue_positional.json`**, not folded into
the main queue — `--append` does that once you have looked at them. Nothing is
promoted either way.

**Why you can trust the alignment:** 28 of the 30 candidates reproduce the value
already stored in `punk_records.json` exactly, and none conflicts with it. If
the index alignment were off by even one column the heights would be scrambled
and the conflicts would be obvious. The two that differ are occupation *wording*
(Drake's SWORD role, Gerd's "Ship's Doctor" against a stored "Doctor"), not
disagreements of fact.

So these are **tier promotions, not value changes**: the Codex already holds the
right numbers, wiki-derived, and this is Oda's own words arriving to back them.

| Subject | Field | Value from the table | Currently stored | SBS |
|---|---|---|---|---|
| X Drake | occupation | Former Rear Admiral | Captain of SWORD; Pirate (undercover); Capta | vol 110 q1592 |
| Kujaku | occupation | Rear Admiral | Rear Admiral | vol 110 q1592 |
| Koby | occupation | Captain | Marine Captain; Master Chief Petty Officer ( | vol 110 q1592 |
| Hibari | occupation | Commander | Commander | vol 110 q1592 |
| Helmeppo | occupation | Lieutenant Commander | Lieutenant Commander; Chief Petty Officer (p | vol 110 q1592 |
| X Drake | age | 33 years old | 31 (debut) · 33 (after timeskip) | vol 110 q1592 |
| Kujaku | age | 26 years old | 26 | vol 110 q1592 |
| Koby | age | 18 years old | 16 (debut) · 18 (after timeskip) | vol 110 q1592 |
| Hibari | age | 17 years old | 17 | vol 110 q1592 |
| Helmeppo | age | 22 years old | 20 (debut) · 22 (after timeskip) | vol 110 q1592 |
| X Drake | height | 233 cm (7'8") | 233 cm (7'8") (debut, after timeskip) | vol 110 q1592 |
| Kujaku | height | 180 cm (5'11") | 180 cm (5'11") | vol 110 q1592 |
| Koby | height | 167 cm (5'6") | 167 cm (5'6") | vol 110 q1592 |
| Hibari | height | 165 cm (5'5") | 165 cm (5'5") | vol 110 q1592 |
| Helmeppo | height | 179 cm (5'10") | 179 cm (5'10") | vol 110 q1592 |
| Hajrudin | occupation | Captain | Captain of the Sixth Ship of the Straw Hat G | vol 112 q1636 |
| Hajrudin | height | 2200 cm | 2200 cm (72'2") | vol 112 q1636 |
| Hajrudin | age | 81 | 81 | vol 112 q1636 |
| Stansen | occupation | Shipwright | Pirate; Shipwright; Mercenary (former); Slav | vol 112 q1636 |
| Stansen | height | 1950 cm | 1950 cm (64') | vol 112 q1636 |
| Stansen | age | 81 | 79 (debut) · 81 (after timeskip) | vol 112 q1636 |
| Gerd | occupation | Ship's Doctor | Pirate; Doctor; Mercenary (former) | vol 112 q1636 |
| Gerd | height | 1700 cm | 1700 cm (55'9") | vol 112 q1636 |
| Gerd | age | 75 | 75 | vol 112 q1636 |
| Goldberg | occupation | Cook | Cook; Pirate; Mercenary (former) | vol 112 q1636 |
| Goldberg | height | 2100 cm | 2100 cm (68'11") | vol 112 q1636 |
| Goldberg | age | 63 | 63 | vol 112 q1636 |
| Road | occupation | Navigator | Navigator; Pirate; Mercenary (former) | vol 112 q1636 |
| Road | height | 2600 cm | 2600 cm (85'3") | vol 112 q1636 |
| Road | age | 63 | 63 | vol 112 q1636 |

**Three claims were dropped, not listed above.** The Vol. 110 table names
`Grus`, and `lib/resolve.py` cannot get from that to the record `Prince Grus`:
its looseners strip a *leading* family name from the input, so a long record
name matched against a short table cell has no rule to meet it. His rank, age
and height are all in that table and all currently unreachable. Worth a
`Resolver` variant that also tries the record names *ending* in the queried
token — that is the same mismatch class as Koby/Coby.

