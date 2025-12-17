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

## Installasjon

Prosjektet bruker [Poetry](https://python-poetry.org/) for pakke- og avhengighetshåndtering.

1.  Naviger til prosjektmappen:
    ```bash
    cd sensorplot
    ```
2.  Installer avhengigheter:
    ```bash
    poetry install
    ```

---

## 1. Bruk av Web-grensesnitt (GUI)

Dette er den anbefalte måten å bruke Sensorplot på for analyse.

### Kjøre appen
```bash
poetry run streamlit run src/sensorplot/app.py
```

### Funksjonalitet i GUI
1.  **Last opp:** Dra og slipp Excel/CSV-filer i sidepanelet.
2.  **Alias:** Gi filene korte navn (f.eks. `L1`, `Baro`).
3.  **Formler:** Skriv regnestykker i tekstboksen:
    * `Nivå = L1.ch1 - Baro.ch1`
    * `Justert = (Data.ch1 * 100) / 9.81`
4.  **Tidsfilter:** Bruk slideren for å justere tidsvinduet. Dette synkroniserer både det interaktive plottet og filen du laster ned.
5.  **Last ned:** Klikk "Last ned" for å få et ferdig formatert bilde av det valgte tidsutsnittet.

---

## 2. Bruk av Kommandolinje (CLI)

For automatisering eller behandling på servere uten skjerm.

### Syntaks
```bash
poetry run sensorplot [OPTIONS]
```

### Argumenter

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
Lag en fil `analyse.yaml`:
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
# pages/05_Sensor_Analyse.py
import streamlit as st
from sensorplot.app import run_app

st.set_page_config(page_title="Sensor Analyse", layout="wide")

st.markdown("# Mitt Dashboard")
# Kjør Sensorplot-grensesnittet her
run_app()
```

---

## Utvikling og Testing

### Kjøre tester
Prosjektet har omfattende tester for fil-lesing, matematikk og sammenslåing av serier.

```bash
poetry run pytest
```