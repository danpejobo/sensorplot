# Sensorplot

**Sensorplot** er et moderne, raskt og fleksibelt kommandolinjeverktøy (CLI) for visualisering og analyse av tidsseriedata. Det støtter både Excel- og CSV-filer, og er optimalisert for å håndtere flere datasett samtidig.

Verktøyet gjør det enkelt å sammenligne sensordata, utføre matematiske korrigeringer (f.eks. barometrisk kompensasjon) og automatisk fjerne støy.

## Funksjonalitet

* **Multiformat-støtte:** Leser både **Excel** (`.xlsx`) og **CSV** (`.csv`) automatisk.
* **Smart CSV-lesing:** Detekterer automatisk start-raden for data i CSV-filer fra loggere (håndterer metadata i toppen).
* **Parallell prosessering:** Laster og behandler flere filer samtidig (multithreading) for maksimal ytelse.
* **Multiseries:** Kan plotte flere uavhengige serier i samme graf (f.eks. to ulike sensorer korrigert mot hvert sitt barometer).
* **Matematiske formler:** Definer regnestykker direkte i terminalen (f.eks. `Vann.ch1 - Baro.ch1`).
* **Automatisk vasking:** Fjerner "outliers" (støy) basert på statistisk Z-score.
* **Server-vennlig:** Kan lagre plott direkte til fil (PNG/PDF) for bruk på servere uten skjerm (headless).

---

## Installasjon

Prosjektet bruker [Poetry](https://python-poetry.org/) for pakke- og avhengighetshåndtering.

### Forutsetninger

* Python 3.10 eller nyere
* Poetry installert (`pip install poetry`)

### Oppsett

1.  Naviger til prosjektmappen:
    ```bash
    cd sensorplot
    ```
2.  Installer avhengigheter:
    ```bash
    poetry install
    ```

---

## Bruk

Du kjører verktøyet ved å bruke `poetry run sensorplot`.

### Syntaks

```bash
poetry run sensorplot --files <ALIAS>=<FILSTI> ... [OPTIONS]
```

### Argumenter

| Flagg | Beskrivelse | Standard (Default) |
| :--- | :--- | :--- |
| `--files` | **Påkrevd.** Liste over filer og alias. Format: `Alias=Filsti` | - |
| `--series` | **Anbefalt.** Liste over serier å plotte. Format: `"Navn=Formel"`. | - |
| `--formel` | Alternativ til `--series` for å plotte kun én enkelt linje. | - |
| `--clean` | Fjerner støy (Z-score). Bruk alene eller med tall (f.eks 4.0). | `--clean` (std: 3.0) |
| `--output` | Lagring/Visning. Se tabell under for oppførsel. | Vis GUI (default) |
| `--tittel` | Setter overskrift på plottet. | "Sensor Plot" |
| `--datecol` | Navn på kolonnen som inneholder dato. | "Date5" |
| `--timecol` | Navn på tidskolonne (`None` hvis samlet). | "Time6" |
| `--datacol` | Navn på datakolonnen du vil lese fra filen. | "ch1" |

### Oppførsel for `--output`

| Kommando | Resultat |
| :--- | :--- |
| `sensorplot ...` (ingen flagg) | Åpner et **GUI-vindu** med plottet (lokal bruk). |
| `sensorplot ... --output` | Lagrer plottet som **`sensorplot.png`** i gjeldende mappe. |
| `sensorplot ... --output graf.pdf` | Lagrer plottet som **`graf.pdf`** (valgfritt navn/sti). |

> **VIKTIG OM FORMELER:**
> Uansett hva datakolonnen heter i filen (f.eks. "LEVEL" eller "Temperatur"), vil programmet internt kalle denne `Alias.ch1`. Bruk alltid `.ch1` i formlene dine.

---

## Eksempler

### 1. Hovedfunksjon: Flere serier (Excel)
Her laster vi inn to sensorfiler (`L1`, `L2`) og én barometerfil (`B`). Vi plotter to linjer i samme graf: begge sensorene korrigert mot samme barometer.

```bash
poetry run sensorplot \
  --files L1=Laksemyra1.xlsx L2=Laksemyra2.xlsx B=Baro.xlsx \
  --series "Laksemyra 1=L1.ch1 - B.ch1" "Laksemyra 2=L2.ch1 - B.ch1" \
  --tittel "Sammenligning av lokasjoner"
```

### 2. CSV-filer med egne kolonnenavn
Hvis du har CSV-filer fra loggere (som ofte har andre kolonnenavn enn standarden), må du spesifisere hvilke kolonner som skal brukes.
* Dato: `Date`
* Tid: `Time`
* Data: `LEVEL`

```bash
poetry run sensorplot \
  --files B="Barologger.csv" L1="Laksemyra1.csv" \
  --series "Korrigert Nivå=L1.ch1 - B.ch1" \
  --datecol Date --timecol Time --datacol LEVEL
```

### 3. Enkelt plott (Hurtigbruk)
Hvis du bare skal plotte én ting, kan du bruke `--formel` i stedet for `--series`.

```bash
poetry run sensorplot \
  --files V=Vann.xlsx B=Baro.xlsx \
  --formel "V.ch1 - B.ch1"
```

### 4. Avansert formel (Enhetskonvertering)
Konverter barometer (kPa) til meter vannsøyle (dele på 9.81) før subtraksjon.

```bash
poetry run sensorplot \
  --files V=Vann.xlsx B=Baro.xlsx \
  --series "Justert nivå=V.ch1 - (B.ch1 / 9.81)"
```

### 5. Server-modus (Lagre til fil)
Fjerner automatisk punkter som er støy (outliers) og lagrer resultatet som et bilde. Nyttig på servere uten skjerm.

```bash
poetry run sensorplot \
  --files D=Data.xlsx \
  --formel "D.ch1" \
  --clean \
  --output plott.png
```

---

## Utvikling og Testing

Prosjektet er bygget med moderne Python-prinsipper (Type Hinting, Dataclasses, Multithreading).

### Kjøre tester
Testene ligger i `tests/`-mappen. For å kjøre dem:

```bash
poetry run pytest
```

### Testdata
For at integrasjonstestene skal fungere, må du legge ekte datafiler i mappen `tests/data/`:
* `tests/data/Baro.xlsx`
* `tests/data/Laksemyra_1.xlsx`