# Phase 1 Retrieval Benchmark

Generated: `2026-11-12T21:12:54.177740+00:00`  
Top-k: `5`

## Summary

| Pipeline | Chunks | Source hit rate | MRR | Evidence coverage |
|---|---:|---:|---:|---:|
| baseline | 44 | 100.0% | 0.875 | 76.7% |
| docling | 63 | 100.0% | 0.875 | 87.5% |

## Comparative interpretation

The metrics evaluate retrieval only; they do not claim that a generated answer is factually correct. Source hit rate measures whether the expected PDF appears in the top-k, MRR rewards higher ranking, and evidence coverage checks whether the retrieved set contains the expected answer-bearing facts.

| Case | Baseline coverage | Docling coverage | Difference |
|---|---:|---:|---:|
| fine-comparison | 100.0% | 100.0% | +0.0% |
| division-comparison | 100.0% | 50.0% | -50.0% |
| wanted-murder | 40.0% | 100.0% | +60.0% |
| historic-counts | 66.7% | 100.0% | +33.3% |

Qualitative review should accompany these values. In particular, inspect whether fine amounts remain attached to their descriptions and legal sections, whether each division retains the correct year/value columns, and whether OCR captures text inside the wanted/missing-person cards. A lower score is a documented finding, not a result to conceal; use the ranked evidence below to explain the failure mode.

## Baseline results

### fine-comparison

What is the fine amount and demerit point penalty for exceeding the speed limit in a school safety zone by 33-49 km/h under Section 76(4), and how does it compare to driving without a seatbelt under Section 72(4)?

- Source found: **True**
- Reciprocal rank: **1.000**
- Evidence coverage: **100.0%** (6/6)
- Retrieved evidence:
  1. `JCF-Fines.pdf, p. 1` score=0.5512 - Source: JCF-Fines Page: 1 CONS# DESCRIPTION FINE AMOUNTPOINTSMCA SECTION OF RTA/REGULATIONS 1 Aid And Abet No Driver’s Licence or Permit $15,000 0 N Section 20(4) 2 Aid And Abet Operating Motor Vehicle Contrary To The Terms Of Insurance Coverage While Acting As A Driving Instructor $30,000 0 N Regulation 180(2) 3 Body Protruding $5,000 0 N Regulation 261(4) 4 Breach of special permit $30,000 0 N Regulation 113(8) 5 Careless Driving Causing Collision $25,000 10 N Section 59(1) 6 Careless Driving
  2. `JCF-Fines.pdf, p. 1` score=0.5512 - Source: JCF-Fines Page: 1 31 Exceeding Speed Limit In Construction Zone; 33-49 Kilometers Per Hour $20,000 6 N Section (77)(3) 32 Exceeding Speed Limit In Construction Zone;16-32 Kilometers Per Hour $12,000 3 N Section 77(3) 33 Exceeding Speed Limit In Construction Zone;50 Or More Kilometers Per Hour $30,000 10 N Section 77(3) 34 Exceeding Speed Limit In School Safety Zone; 16 To 32 Kilometers Per Hour $12,000 3 N Section 76(4) 35 Exceeding Speed Limit In School Safety Zone; 33 To 49 Kilometers
  3. `JCF-Fines.pdf, p. 1` score=0.5509 - Source: JCF-Fines Page: 1 8 Carrying passenger on motor cycle on any part other than the sidecar $5,000 0 N Regulation 261(4) 9 Carrying Person Otherwise Than By Sitting Astride On Motor Cycle $5,000 0 N Section 67(2) 10 Causing Motor Cycle To Be Driven On One Wheel Only $5,000 3 N Section 67(2) 11 Child Without Child Restraint System In Motor Vehicle $5,000 4 N Section 73(2) 12 Crossing From A Minor Road To Major Road So As To Obstruct Traffic $8,000 3 N Section 54(4)b 13 Crossing Road So As To
  4. `JCF-Fines.pdf, p. 2` score=0.5481 - Source: JCF-Fines Page: 2 59 Failing To Keep Left Or Nearside Of The Road When Being Overtaken $5,000 3 N Section 57(5)(a) 60 Failing To Keep Right Or Offside Of Other Traffic Whilst Overtaking $5,000 3 N Section 57(5)(b) 61 Failing to label protective device $5,000 0 N Regulation 276(4) 62 Failing To Obey Constable Command $5,000 1 N Section 91(2) 63 Failing To Observe Silent Zone $5,000 2 N Section 75(1) 64 Failing To Observe Stop For Crossing When Required By A School Crossing Warden $12,000
  5. `JCF-Fines.pdf, p. 1` score=0.5416 - Source: JCF-Fines Page: 1 18 Driver Failing to Cause Passenger To Wear Seatbelt $2,000 2 N Section 72(4) 19 Driver Not Ensuring Pillion Wears Helmet $8,000 2 N Section 74(3) 20 Driver Overtaking Without A Clear View $10,000 3 N Section 57(5)(d)(i) 21 Driving a non-emergency vehicle over a Jamaica Fire Brigade hose laid on the road for the use at a fire without consent of a Constable or other person controlling traffic or Superintendent or other officer of the JFB $5,000 0 N Regulation 284(2)
### division-comparison

Compare the 2025 and 2026 murder counts for St. James versus Westmoreland division. Which division recorded an increase and by what percentage?

- Source found: **True**
- Reciprocal rank: **1.000**
- Evidence coverage: **100.0%** (2/2)
- Retrieved evidence:
  1. `JCF-Murder-Stats.pdf, p. 1` score=0.5904 - Source: JCF-Murder-Stats Page: 1 Division Murder2025 Murder2026 +/- % Shooting2025 Shooting2026 +/- % Personsinjured2025 PersonInjured2026 Rape2025 Rape2026 +/- % Robbery2025 Robbery2026 +/- % Break-in2025 Break-In2026 +/- % GrandTotal2025 GrandTotal2026 +/- % Westmoreland 33 23 -10 -30.3% 45 33 -12 -26.7% 23 26 18 16 -2 -11.1% 22 13 -9 -40.9% 25 23 -2 -8.0% 143 108 -35 -24.5% Hanover 19 14 -5 -26.3% 19 12 -7 -36.8% 6 7 16 9 -7 -43.8% 13 5 -8 -61.5% 34 24 -10 -29.4% 101 64 -37 -36.6% St. James 4
  2. `JCF-Murder-Stats.pdf, p. 1` score=0.5598 - Source: JCF-Murder-Stats Page: 1 Grand Total 570 439 -131 -23.0% 581 428 -153 -26.3% 383 276 328 290 -38 -11.6% 621 426 -195 -31.4% 961 836 -125 -13.0% 3061 2419 -642 -21.0% 11/8/26, 7:47 AM Statistics – Jamaica Constabulary Force https://jcf.gov.jm/stats-2/ 1/1
  3. `JCF-Murder-Stats.pdf, p. 1` score=0.4993 - Source: JCF-Murder-Stats Page: 1 St. Mary 23 14 -9 -39.1% 13 9 -4 -30.8% 10 6 17 17 0 0.0% 20 18 -2 -10.0% 26 47 21 80.8% 99 105 6 6.1% Portland 9 5 -4 -44.4% 7 3 -4 -57.1% 4 2 11 19 8 72.7% 9 5 -4 -44.4% 51 58 7 13.7% 87 90 3 3.4% St. Elizabeth 13 28 15 115.4% 14 15 1 7.1% 10 8 24 14 -10 -41.7% 24 16 -8 -33.3% 95 73 -22 -23.2% 170 146 -24 -14.1% Manchester 30 28 -2 -6.7% 22 28 6 27.3% 11 12 20 11 -9 -45.0% 23 18 -5 -21.7% 108 41 -67 -62.0% 203 126 -77 -37.9% Clarendon 34 29 -5 -14.7% 33 27 -6 -
  4. `JCF-Murder-Stats.pdf, p. 1` score=0.4854 - Source: JCF-Murder-Stats Page: 1 Kingston Western 30 20 -10 -33.3% 29 37 8 27.6% 22 24 8 14 6 75.0% 5 9 4 80.0% 6 9 3 50.0% 78 89 11 14.1% St. Andrew Central 26 29 3 11.5% 29 25 -4 -13.8% 19 10 16 5 -11 -68.8% 54 30 -24 -44.4% 28 27 -1 -3.6% 153 116 -37 -24.2% St. Andrew South 68 47 -21 -30.9% 73 36 -37 -50.7% 54 27 14 14 0 0.0% 47 38 -9 -19.1% 41 42 1 2.4% 243 177 -66 -27.2% St. Andrew North 32 9 -23 -71.9% 41 12 -29 -70.7% 17 8 17 2 -15 -88.2% 51 19 -32 -62.7% 109 59 -50 -45.9% 250 101 -149 -5
  5. `JCF-Murder-Counts.pdf, p. 4` score=0.4836 - Source: JCF-Murder-Counts Page: 4 Y E A R M U R D E R 2015 1,209.00 2016 1,355.00 2017 1,647.00 2018 1,291.00 2019 1,340.00 2020 1,334.00 2021 1,479.00 2022 1,516.00 2023 1,406.00 2024 1,147.00 2025 675.00 11/9/26, 4:17 AM about:blank about:blank 4/4
### wanted-murder

List all individuals currently listed as wanted for Murder in the JCF registry, and state the official emergency tip line numbers provided for citizen reporting.

- Source found: **True**
- Reciprocal rank: **1.000**
- Evidence coverage: **40.0%** (4/10)
- Retrieved evidence:
  1. `JCF-Wanted Persons.pdf, p. 1` score=0.5995 - Source: JCF-Wanted Persons Page: 1 Police Emergency 119 Crime Stop 311 Tip Line 876-838-3589 INTERPOL Kingston GOVPortal Police Record FAQs Contact WANTED PERSONS  Contact Us DAVE EDWARDS Wanted for Murder LEROY GRAY Wanted for Assault at Common Law ALEX THOMPSON Wanted for Wounding with Intent Wanted Persons You are here: Home / Alerts / Wanted Persons Jamaica Constabulary Force People, Quality and Technology Home About News Alerts Resources Careers Contact Apply for Police Record 11/9/26,
  2. `JCF-Missing Persons.pdf, p. 1` score=0.5937 - Source: JCF-Missing Persons Page: 1 Police Emergency 119 Crime Stop 311 Tip Line 876-838-3589 INTERPOL Kingston GOVPortal Police Record FAQs Contact MISSING PERSONS You are here: Home / Alerts Jamaica Constabulary Force People, Quality and Technology Home About News Alerts Resources Careers Contact Apply for Police Record 11/9/26, 4:35 AM Alerts – Jamaica Constabulary Force https://jcf.gov.jm/missing-person-3/ 1/6
  3. `JCF-Murder-Stats.pdf, p. 1` score=0.5575 - Source: JCF-Murder-Stats Page: 1 Grand Total 570 439 -131 -23.0% 581 428 -153 -26.3% 383 276 328 290 -38 -11.6% 621 426 -195 -31.4% 961 836 -125 -13.0% 3061 2419 -642 -21.0% 11/8/26, 7:47 AM Statistics – Jamaica Constabulary Force https://jcf.gov.jm/stats-2/ 1/1
  4. `JCF-Wanted Persons.pdf, p. 3` score=0.5060 - Source: JCF-Wanted Persons Page: 3 JEVAUGHN CAMPBELL Wanted for Murder & Wounding with Intent DAVE EDWARDS Wanted for Murder CONROY ROBINSON Wanted for Attempted Murder CHARLES THOMPSON Wanted for Wounding with Intent 11/9/26, 4:29 AM Wanted Persons – Jamaica Constabulary Force https://jcf.gov.jm/missing-person-3/missing-person-2/ 3/4
  5. `JCF-Murder-Counts.pdf, p. 4` score=0.5059 - Source: JCF-Murder-Counts Page: 4 Y E A R M U R D E R 2015 1,209.00 2016 1,355.00 2017 1,647.00 2018 1,291.00 2019 1,340.00 2020 1,334.00 2021 1,479.00 2022 1,516.00 2023 1,406.00 2024 1,147.00 2025 675.00 11/9/26, 4:17 AM about:blank about:blank 4/4
### historic-counts

What was the national murder total in Jamaica for the years 1980, 2005, and 2024 based on the JCF historical murder counts PDF?

- Source found: **True**
- Reciprocal rank: **0.500**
- Evidence coverage: **66.7%** (2/3)
- Retrieved evidence:
  1. `JCF-Murder-Stats.pdf, p. 1` score=0.7565 - Source: JCF-Murder-Stats Page: 1 Grand Total 570 439 -131 -23.0% 581 428 -153 -26.3% 383 276 328 290 -38 -11.6% 621 426 -195 -31.4% 961 836 -125 -13.0% 3061 2419 -642 -21.0% 11/8/26, 7:47 AM Statistics – Jamaica Constabulary Force https://jcf.gov.jm/stats-2/ 1/1
  2. `JCF-Murder-Counts.pdf, p. 2` score=0.6350 - Source: JCF-Murder-Counts Page: 2 Y E A R M U R D E R 1979 351.00 1980 889.00 1981 490.00 1982 405.00 1983 424.00 1984 484.00 1985 434.00 1986 449.00 1987 442.00 1988 414.00 1989 439.00 1990 542.00 1991 561.00 1992 629.00 1993 654.00 1994 690.00 1995 780.00 1996 925.00 11/9/26, 4:17 AM about:blank about:blank 2/4
  3. `JCF-Murder-Counts.pdf, p. 4` score=0.6163 - Source: JCF-Murder-Counts Page: 4 Y E A R M U R D E R 2015 1,209.00 2016 1,355.00 2017 1,647.00 2018 1,291.00 2019 1,340.00 2020 1,334.00 2021 1,479.00 2022 1,516.00 2023 1,406.00 2024 1,147.00 2025 675.00 11/9/26, 4:17 AM about:blank about:blank 4/4
  4. `JCF-Murder-Counts.pdf, p. 1` score=0.6140 - Source: JCF-Murder-Counts Page: 1 Y E A R M U R D E R 1962 63.00 1963 70.00 1964 70.00 1965 65.00 1966 111.00 1967 102.00 1968 110.00 1969 153.00 1970 152.00 1971 145.00 1972 188.00 1973 232.00 1974 195.00 1975 266.00 1976 367.00 1977 409.00 1978 381.00 11/9/26, 4:17 AM about:blank about:blank 1/4
  5. `JCF-Murder-Stats.pdf, p. 1` score=0.5848 - Source: JCF-Murder-Stats Page: 1 Division Murder2025 Murder2026 +/- % Shooting2025 Shooting2026 +/- % Personsinjured2025 PersonInjured2026 Rape2025 Rape2026 +/- % Robbery2025 Robbery2026 +/- % Break-in2025 Break-In2026 +/- % GrandTotal2025 GrandTotal2026 +/- % Westmoreland 33 23 -10 -30.3% 45 33 -12 -26.7% 23 26 18 16 -2 -11.1% 22 13 -9 -40.9% 25 23 -2 -8.0% 143 108 -35 -24.5% Hanover 19 14 -5 -26.3% 19 12 -7 -36.8% 6 7 16 9 -7 -43.8% 13 5 -8 -61.5% 34 24 -10 -29.4% 101 64 -37 -36.6% St. James 4

## Docling results

### fine-comparison

What is the fine amount and demerit point penalty for exceeding the speed limit in a school safety zone by 33-49 km/h under Section 76(4), and how does it compare to driving without a seatbelt under Section 72(4)?

- Source found: **True**
- Reciprocal rank: **1.000**
- Evidence coverage: **100.0%** (6/6)
- Retrieved evidence:
  1. `JCF-Fines.pdf, p. 1` score=0.6743 - Source: JCF-Fines | - | 29, SECTION OF RTA/REGULATIONS = Section 122(3). 30, DESCRIPTION = Driving/Riding in a Motor Vehicle Without Seatbelt On. 30, FINE = $2,000. 30, POINTS = 2. 30, MCA = N. 30, SECTION OF RTA/REGULATIONS = Section 72(4). 31, DESCRIPTION = Exceeding Speed Limit In Construction Zone; 33-49 Kilometers Per Hour. 31, FINE = $20,000. 31, POINTS = 6. 31, MCA = N. 31, SECTION OF RTA/REGULATIONS = Section (77)(3). 32, DESCRIPTION = Exceeding Speed Limit In Construction Zone;16-32 Ki
  2. `JCF-Fines.pdf, p. 1` score=0.6551 - Source: JCF-Fines | - | = $12,000. 34, POINTS = 3. 34, MCA = N. 34, SECTION OF RTA/REGULATIONS = Section 76(4). 35, DESCRIPTION = Exceeding Speed Limit In School Safety Zone; 33 To 49 Kilometers Per Hour. 35, FINE = $20,000. 35, POINTS = 6. 35, MCA = N. 35, SECTION OF RTA/REGULATIONS = Section 76(4). 36, DESCRIPTION = Exceeding Speed Limit In School Safety Zone; 50 or More. 36, FINE = $30,000. 36, POINTS = 10. 36, MCA = N. 36, SECTION OF RTA/REGULATIONS = Section 76(4). , DESCRIPTION = Kilometr
  3. `JCF-Fines.pdf, p. 1` score=0.5929 - Source: JCF-Fines | - | N. 10, SECTION OF RTA/REGULATIONS = Section 67(2). 11, DESCRIPTION = Child Without Child Restraint System In Motor Vehicle. 11, FINE = $5,000. 11, POINTS = 4. 11, MCA = N. 11, SECTION OF RTA/REGULATIONS = Section 73(2). 12, DESCRIPTION = Crossing From A Minor Road To Major Road So As To Obstruct Traffic. 12, FINE = $8,000. 12, POINTS = 3. 12, MCA = N. 12, SECTION OF RTA/REGULATIONS = Section 54(4)b. 13, DESCRIPTION = Crossing Road So As To Obstruct Traffic. 13, FINE = $9
  4. `JCF-Fines.pdf, p. 1` score=0.5670 - Source: JCF-Fines | - | 2. 37, MCA = N. 37, SECTION OF RTA/REGULATIONS = Section 55(3). 39, DESCRIPTION = Excess Noise. 39, FINE = $10,000. 39, POINTS = 0. 39, MCA = N. 39, SECTION OF RTA/REGULATIONS = . , DESCRIPTION = Exceeding Speed Limit; 50 Or More Kilometers Per Hour. , FINE = $15,000. , POINTS = 6. , MCA = N. , SECTION OF RTA/REGULATIONS = Regulation 247(7). 40 41, DESCRIPTION = Excess Weight 1001-5000 Kilogram. 40 41, FINE = $100,000. 40 41, POINTS = 0. 40 41, MCA = N. 40 41, SECTION OF
  5. `JCF-Fines.pdf, p. 1` score=0.5649 - Source: JCF-Fines | - | 15, POINTS = 6. 15, MCA = N. 15, SECTION OF RTA/REGULATIONS = Section 52(2)(a). 16, DESCRIPTION = Drawing More Than Prescribed Number of Trailers. 16, FINE = $12,000. 16, POINTS = 4. 16, MCA = N. 16, SECTION OF RTA/REGULATIONS = Section 68(3). 17, DESCRIPTION = Driver Accompanying Learner Driver Having Excess Alcohol. 17, FINE = $12,000. 17, POINTS = 0. 17, MCA = N. 17, SECTION OF RTA/REGULATIONS = Section 24(4). 18, DESCRIPTION = Driver Failing to Cause Passenger To Wea
### division-comparison

Compare the 2025 and 2026 murder counts for St. James versus Westmoreland division. Which division recorded an increase and by what percentage?

- Source found: **True**
- Reciprocal rank: **1.000**
- Evidence coverage: **50.0%** (1/2)
- Retrieved evidence:
  1. `JCF-Murder-Stats.pdf, p. 1` score=0.5784 - Source: JCF-Murder-Stats | - | +/- = . Westmoreland, % = -24.5%. Hanover, Murder 2025 = 19. Hanover, Murder 2026 = 14. Hanover, +/- = -5. Hanover, % = -26.3% 19. Hanover, Shooting 2025 = . Hanover, Shooting 2026 = 12. Hanover, +/- = -7. Hanover, % = -36.8%. Hanover, Persons injured 2025 = 6. Hanover, Person Injured 2026 = 7. Hanover, Rape 2025 = 16. Hanover, Rape 2026 = 9. Hanover, +/- = -7. Hanover, % = -43.8% 13. Hanover, Robbery 2025 Robbery 2026 = 5. Hanover, +/- % = -8 -61.5% 34. Hanover,
  2. `JCF-Murder-Stats.pdf, p. 1` score=0.5550 - Source: JCF-Murder-Stats | - | Murder 2026 = 54. St. James, +/- = 8. St. James, % = 17.4% 47. St. James, Shooting 2025 = . St. James, Shooting 2026 = 50. St. James, +/- = 3. St. James, % = 6.4%. St. James, Persons injured 2025 = 36. St. James, Person Injured 2026 = 35. St. James, Rape 2025 = 17. St. James, Rape 2026 = 19. St. James, +/- = 2. St. James, % = 11.8% 59. St. James, Robbery 2025 Robbery 2026 = 38. St. James, +/- % = -21 -35.6% 36. St. James, Break- in 2025 Break- 2026 = 62. St. James
  3. `JCF-Murder-Stats.pdf, p. 1` score=0.5427 - Source: JCF-Murder-Stats | - | | Westmoreland, Murder 2025 = 33. Westmoreland, Murder 2026 = 23. Westmoreland, +/- = -10. Westmoreland, % = -30.3% 45. Westmoreland, Shooting 2025 = . Westmoreland, Shooting 2026 = 33. Westmoreland, +/- = -12. Westmoreland, % = -26.7%. Westmoreland, Persons injured 2025 = 23. Westmoreland, Person Injured 2026 = 26. Westmoreland, Rape 2025 = 18. Westmoreland, Rape 2026 = 16. Westmoreland, +/- = -2. Westmoreland, % = -11.1% 22. Westmoreland, Robbery 2025 Robbery 202
  4. `JCF-Murder-Stats.pdf, p. 1` score=0.5424 - Source: JCF-Murder-Stats | - | -11.6%. Grand Total, % = 621. Grand Total, Robbery 2025 Robbery 2026 = 426. Grand Total, +/- % = -31.4%. Grand Total, Break- in 2025 Break- 2026 = 961. Grand Total, = -125. Grand Total, In +/- = -13.0%. Grand Total, % = 3061. Grand Total, Grand Total 2025 Grand Total 2026 = 2419. Grand Total, +/- = -642. Grand Total, % = -21.0% |
  5. `JCF-Murder-Stats.pdf, p. 1` score=0.5357 - Source: JCF-Murder-Stats | - | Catherine South, +/- % = -16 -23.9% 57. St. Catherine South, Break- in 2025 Break- 2026 = 39. St. Catherine South, = -18 -31.6%. St. Catherine South, In +/- = 257. St. Catherine South, % = . St. Catherine South, Grand Total 2025 Grand Total 2026 = 187. St. Catherine South, +/- = -70. St. Catherine South, % = -27.2%. St. Thomas, Murder 2025 = 16. St. Thomas, Murder 2026 = 9. St. Thomas, +/- = -7. St. Thomas, % = -43.8%. St. Thomas, Shooting 2025 = 14. St. Thomas, S
### wanted-murder

List all individuals currently listed as wanted for Murder in the JCF registry, and state the official emergency tip line numbers provided for citizen reporting.

- Source found: **True**
- Reciprocal rank: **0.500**
- Evidence coverage: **100.0%** (10/10)
- Retrieved evidence:
  1. `JCF-Missing Persons.pdf, p. 1` score=0.6106 - Source: JCF-Missing Persons Police Emergency 119 Crime Stop 311 Tip Line 876-838-3589 INTERPOL Kingston GOVPortal Police Record FAQs Contact Home About News Alerts [Contact](https://jcf.gov.jm/contact/)
  2. `JCF-Wanted Persons.pdf, p. 1` score=0.5896 - Source: JCF-Wanted Persons WANTED PERSONS [ Contact Us](https://jcf.gov.jm/contact/) DAVE EDWARDS Wanted for Murder LEROY GRAY Wanted for Assault at Common Law ALEX THOMPSON Wanted for Wounding with Intent Resources V Careers Apply for Police Record You are here: Home / Alerts / Wanted Persons L PATRICK PATTERSON Wanted For: Frau ulent Conversion Patrick Patterson Wanted for Fraudulent Conversion Jermaine Richards Wanted for Murder Derrick Johnson Wanted for Murder Raheem Brown Wanted for Murde
  3. `JCF-Wanted Persons.pdf, p. 1` score=0.5796 - Source: JCF-Wanted Persons Police Emergency 119 Crime Stop 311 Tip Line 876-838-3589 INTERPOL Kingston GOVPortal Police Record FAQs Contact
  4. `JCF-Wanted Persons.pdf, p. 1` score=0.5567 - Source: JCF-Wanted Persons Wanted Persons Home About News Alerts [Contact](https://jcf.gov.jm/contact/)
  5. `JCF-Wanted Persons.pdf, p. 3` score=0.5382 - Source: JCF-Wanted Persons JEVAUGHN CAMPBELL Wanted for Murder & Wounding with Intent
### historic-counts

What was the national murder total in Jamaica for the years 1980, 2005, and 2024 based on the JCF historical murder counts PDF?

- Source found: **True**
- Reciprocal rank: **1.000**
- Evidence coverage: **100.0%** (3/3)
- Retrieved evidence:
  1. `JCF-Murder-Counts.pdf, p. 1` score=0.6690 - Source: JCF-Murder-Counts 1962, MURDER = 63.00. 1963, MURDER = 70.00. 1964, MURDER = 70.00. 1965, MURDER = 65.00. 1966, MURDER = 111.00. 1967, MURDER = 102.00. 1968, MURDER = 110.00. 1969, MURDER = 153.00. 1970, MURDER = 152.00. 1971, MURDER = 145.00. 1972, MURDER = 188.00. 1973, MURDER = 232.00. 1974, MURDER = 195.00. 1975, MURDER = 266.00. 1976, MURDER = 367.00. 1977, MURDER = 409.00. 1978, MURDER = 381.00
  2. `JCF-Murder-Counts.pdf, p. 2` score=0.6626 - Source: JCF-Murder-Counts 1979, MURDER = 351.00. 1980, MURDER = 889.00. 1981, MURDER = 490.00. 1982, MURDER = 405.00. 1983, MURDER = 424.00. 1984, MURDER = 484.00. 1985, MURDER = 434.00. 1986, MURDER = 449.00. 1987, MURDER = 442.00. 1988, MURDER = 414.00. 1989, MURDER = 439.00. 1990, MURDER = 542.00. 1991, MURDER = 561.00. 1992, MURDER = 629.00. 1993, MURDER = 654.00. 1994, MURDER = 690.00. 1995, MURDER = 780.00. 1996, MURDER = 925.00
  3. `JCF-Murder-Counts.pdf, p. 4` score=0.6530 - Source: JCF-Murder-Counts YEAR, 1 = MURDER. 2015, 1 = 1,209.00. 2016, 1 = 1,355.00. 2017, 1 = 1,647.00. 2018, 1 = 1,291.00. 2019, 1 = 1,340.00. 2020, 1 = 1,334.00. 2021, 1 = 1,479.00. 2022, 1 = 1,516.00. 2023, 1 = 1,406.00. 2024, 1 = 1,147.00. 2025, 1 = 675.00
  4. `JCF-Murder-Counts.pdf, p. 3` score=0.6089 - Source: JCF-Murder-Counts 1997, MURDER = 1,038.00. 1998, MURDER = 953.00. 1999, MURDER = 849.00. 2000, MURDER = 887.00. 2001, MURDER = 1,093.00. 2002, MURDER = 1,045.00. 2003, MURDER = 976.00. 2004, MURDER = 1,471.00. 2005, MURDER = 1,674.00. 2006, MURDER = 1,340.00. 2007, MURDER = 1,584.00. 2008, MURDER = 1,620.00. 2009, MURDER = 1,683.00. 2010, MURDER = 1,449.00. 2011, MURDER = 1,133.00. 2012, MURDER = 1,102.00. 2013, MURDER = 1,202.00. 2014, MURDER = 1,006.00
  5. `JCF-Murder-Stats.pdf, p. 1` score=0.5936 - Source: JCF-Murder-Stats | - | -50.0%. Kingston Central, Shooting 2025 = 11. Kingston Central, Shooting 2026 = 14. Kingston Central, +/- = 3. Kingston Central, % = 27.3%. Kingston Central, Persons injured 2025 = 14. Kingston Central, Person Injured 2026 = 13. Kingston Central, Rape 2025 = 7. Kingston Central, Rape 2026 = 1. Kingston Central, +/- = -6. Kingston Central, % = -85.7% 55. Kingston Central, Robbery 2025 Robbery 2026 = 42. Kingston Central, +/- % = -13 -23.6%. Kingston Central, Break-
