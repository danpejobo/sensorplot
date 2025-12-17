# Sensorplot

**Sensorplot** er et kraftig verktøy for visualisering, analyse og korrigering av tidsseriedata fra sensorer. Prosjektet tilbyr nå to bruksmåter: et moderne **Web-grensesnitt (GUI)** for interaktiv analyse, og et effektivt **Kommandolinjeverktøy (CLI)** for batch-prosessering.

## Hovedfunksjoner

* **Hybrid Visning:**
    * 🖥️ **Interaktivt:** Zoom, panorer og inspiser data med Plotly i nettleseren.
    * 📄 **Rapport:** Last ned høyoppløselige, statiske PNG-bilder (Matplotlib) perfekt formatert for Word/PowerPoint.
* **Multiformat:** Leser automatisk både **Excel** (`.xlsx`) og **CSV** (`.csv`) fra ulike loggere (norsk/internasjonalt format).
* **Avansert Matematikk:** Definer korreksjonsformler direkte (f.eks. `Vannstand = Logger.ch1 - Baro.ch1`). Håndterer automatisk "norsk komma" i tall.
* **Støyvask:** Fjerner automatisk "outliers" (støy) basert på statistisk Z-score.
* **Sammenslåing:** Syr automatisk sammen flere filer (f.eks. 2023 og 2024) til én lang tidslinje hvis de har samme serienavn.
* **Modulær:** Kan kjøres alene eller importeres som en side i en annen Streamlit-app.

---

## Kom i gang (Steg-for-steg)

### 1. Last ned og installer
For at dette verktøyet skal virke, trenger PC-en din to **Python** og **Poetry**.

1.  **Installer Python:** [Last ned her](https://www.python.org/downloads/) (Husk å krysse av for *"Add Python to PATH"* under installasjonen). Eller last ned direkte fra windows store eller linux pakke distributør
2.  **Installer Poetry:** Åpne PowerShell (Windows) eller Terminal (Mac) og lim inn:
    * *Windows:* `(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -`
    * *Mac/Linux:* `curl -sSL https://install.python-poetry.org | python3 -`

### 2. Klargjør Sensorplot
1.  Åpne en terminal (Ledetekst/PowerShell) og gå inn i mappen der du har lagret dette prosjektet:
    ```bash
    cd sensorplot
    ```
2.  Be datamaskinen hente alt som trengs (dette gjør du bare én gang):
    ```bash
    poetry install
    ```
    *(Ser du masse tekst som ruller over skjermen? Det er bra! Da installeres pakkeavhengighetene som trengs!)*

---

## Bruk av Web-grensesnitt (GUI)

Dette er den enkleste måten å bruke Sensorplot på for analyse. Du får opp et vindu i nettleseren din hvor du kan klikke og styre alt.

1.  **Start appen:** Skriv følgende i terminalen:
    ```bash
    poetry run sensorplot-gui
    ```
2.  En nettside skal nå åpne seg automatisk. Hvis ikke, kopier lenken som vises i terminalen (f.eks. `http://localhost:8501`) inn i nettleseren din.

### Funksjonalitet i GUI
1.  **Last opp:** Dra og slipp Excel/CSV-filer i sidepanelet.
2.  **Alias/kallenavn:** Gi filene korte navn (f.eks. `L1`, `Baro`) som brukes til å referere filen i steg 4.
3.  **Konfigurasjon av kolonner:** Sjekk at `Dato`, `Tid` og `Data` kolonnene har korrekt navn i forhold til kolonnenavnene i de opplastede filene. Dette navnet brukes til `datakolonne` feltet i steg 4.
4.  **Formler:** Skriv regnestykker i tekstboksen - en formel per linje:
    * Dette er formatet: `Legende-tekst = ALIAS.datakolonne - ALIAS.datakolonne`
    * Eksempler:
    * `Nivå = L1.ch1 - (Baro.ch1/9,81)`
    * `Justert = (Data.ch1 * 100) / 9.81`
5.  **Tidsfilter:** Bruk slideren for å justere tidsvinduet. Dette synkroniserer både det interaktive plottet og filen du laster ned.
6.  **Last ned:** Klikk "Last ned" for å få et ferdig formatert bilde av det valgte tidsutsnittet.

---

## 2. Bruk av Kommandolinje (CLI)

For automatisering eller behandling på servere uten skjerm.

### Syntaks
```bash
poetry run sensorplot [OPTIONS]
```
Print hjelpemeny:
```bash
poetry run sensorplot --help
```

### OPTIONS

| Flagg | Beskrivelse | Eksempel |
| :--- | :--- | :--- |
| `--config`, `-c` | **Anbefalt.** Sti til YAML-konfigurasjonsfil. | `-c oppsett.yaml` |
| `--files` | Liste over filer og alias (hvis ikke config brukes). | `L=Data.xlsx` |
| `--series` | Liste over serier å plotte. | `"Nivå=L.ch1-B.ch1"` |
| `--clean` | Fjerner støy (Z-score). | `--clean 3.0` |
| `--output` | Lagrer plott til fil. | `--output figur.png` |
| `--x-interval`| Tving etikett-intervall på x-akse. | `1M` (Måned), `2W` (Uker) |
| `--tittel` | Setter overskrift på plottet. | "Min Analyse" |

### Eksempel med Config-fil (Anbefalt)
Lag en fil f.eks `analyse.yaml`. Det ligger en eksempelfil her `example/example_config.yaml`:
```yaml
files:
  L1: "data/Laksmyra.xlsx"
  B: "data/Baro.csv"
series:
  - label: "Korrigert Vannstand"
    formula: "L1.ch1 - B.ch1"
settings:
  title: "Analyse 2024"
  x_interval: "1M"
```
Kjør deretter:
```bash
poetry run sensorplot -c analyse.yaml
```

---

## 3. Integrasjon (Utviklere)

Sensorplot er designet for å kunne være en "modul" i større systemer.

### Importere i en annen Streamlit-app
Hvis du har et eksisterende dashboard, kan du legge til Sensorplot som en egen side:

```python
# pages/Sensor_Analyse.py
import streamlit as st
from sensorplot.app import run_app

st.set_page_config(page_title="Sensor Analyse", layout="wide")

st.markdown("# Mitt Dashboard")
# Kjør Sensorplot-grensesnittet her
run_app()
```

Et eksempel på dette finnes her `example/example_embed-app.py`

---

## Utvikling og Testing

### Kjøre tester
Prosjektet har omfattende tester for fil-lesing, matematikk og sammenslåing av serier.

```bash
poetry run pytest
```