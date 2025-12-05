# Sensorplot

**Sensorplot** er et kommandolinjeverktøy (CLI) skrevet i Python for å visualisere og analysere tidsseriedata fra sensorer (Excel-filer).

Verktøyet er designet for å enkelt sammenligne data fra ulike filer, utføre matematiske korrigeringer (f.eks. barometrisk kompensasjon) og automatisk rense data for støy. Det støtter både interaktiv visning (GUI) og lagring til fil (headless/server).

## Funksjonalitet

* **Tidssynkronisering:** Slår automatisk sammen flere datasett basert på nærmeste tidspunkt (håndterer ulik samplingsrate).
* **Matematiske formler:** Lar deg definere regnestykker direkte i terminalen (f.eks. `Vann.ch1 - Baro.ch1`).
* **Automatisk vasking:** Fjerner "outliers" (ekstreme verdier/støy) basert på statistisk Z-score.
* **Fleksibel import:** Støtter egendefinerte kolonnenavn for dato, tid og data.
* **Lagring:** Kan lagre plott som bildefil (PNG, PDF, etc.) – perfekt for remote servere eller VS Code.

---

## Installasjon

Dette prosjektet bruker [Poetry](https://python-poetry.org/) for pakke- og avhengighetshåndtering.

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
poetry run sensorplot --files <ALIAS>=<FILSTI> ... --formel "<FORMEL>" [OPTIONS]
```

### Argumenter

| Flagg | Beskrivelse | Standard (Default) |
| :--- | :--- | :--- |
| `--files` | **Påkrevd.** Liste over filer og alias. Format: `Alias=Filsti` | - |
| `--formel` | **Påkrevd.** Matematisk formel. NB: Bruk alltid `.ch1` i formelen (se under). | - |
| `--output` | Lagring/Visning. Se tabell under for oppførsel. | Vis GUI (None) |
| `--clean` | Fjerner støy (Z-score). Bruk alene eller med tall (f.eks 4.0). | 3.0 (hvis flagg er satt) |
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
> Selv om du leser data fra en kolonne som heter "Temperatur" (via `--datacol`), vil programmet internt kalle denne `Alias.ch1` for å gjøre formelskriving enklere.
>
> **Riktig:** `--formel "A.ch1 - B.ch1"`
> **Feil:** `--formel "A.Temperatur - B.Trykk"`

---

## Eksempler

### 1. Standard bruk (GUI / Lokal PC)
Her laster vi inn `Baro.xlsx` og `Laksemyra.xlsx`. Siden vi ikke spesifiserer kolonnenavn, brukes standardene. Plottet vises i et popup-vindu.

```bash
poetry run sensorplot \
  --files B=Baro.xlsx L="Laksemyra 1.xlsx" \
  --formel "L.ch1 - B.ch1" \
  --tittel "Vannstand korrigert for lufttrykk"
```

### 2. Kjøring på Server / Remote (Lagre til fil)
På en server uten skjerm (headless) eller via VS Code Remote, vil du lagre plottet i stedet for å vise det.

```bash
# Lagrer til standardfilen 'sensorplot.png'
poetry run sensorplot --files B=Baro.xlsx --formel "B.ch1" --output

# Lagrer til spesifikt navn
poetry run sensorplot --files B=Baro.xlsx --formel "B.ch1" --output rapport_uke42.png
```

### 3. Fjerne støy (Cleaning)
Hvis sensoren har logget feilverdier, bruk `--clean`.

```bash
poetry run sensorplot \
  --files Data=MinFil.xlsx \
  --formel "Data.ch1" \
  --clean
```

### 4. Egendefinerte kolonnenavn
Hvis du har en fil med norske kolonnenavn: `Dato`, `Klokkeslett` og `Nivå`.

```bash
poetry run sensorplot \
  --files MinFil=Data.xlsx \
  --formel "MinFil.ch1" \
  --datecol Dato \
  --timecol Klokkeslett \
  --datacol Nivå
```

---

## Utvikling og Testing

Vi bruker `pytest` for automatisk testing.

### Kjøre tester
Testene ligger i `tests/`-mappen. For å kjøre dem:

```bash
poetry run pytest
```

### Testdata
For at integrasjonstestene skal fungere, må du legge ekte datafiler i mappen `tests/data/`:
* `tests/data/Baro.xlsx`
* `tests/data/Laksemyra 1.xlsx`