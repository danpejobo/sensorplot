# Sensorplot

**Sensorplot** er et kommandolinjeverktøy (CLI) skrevet i Python for å visualisere og analysere tidsseriedata fra sensorer (Excel-filer).

Verktøyet er designet for å enkelt sammenligne data fra ulike filer, utføre matematiske korrigeringer (f.eks. barometrisk kompensasjon) og automatisk rense data for støy.

## Funksjonalitet

* **Tidssynkronisering:** Slår automatisk sammen flere datasett basert på nærmeste tidspunkt (håndterer ulik samplingsrate).
* **Matematiske formler:** Lar deg definere regnestykker direkte i terminalen (f.eks. `Vann.ch1 - Baro.ch1`).
* **Automatisk vasking:** Fjerner "outliers" (ekstreme verdier/støy) basert på statistisk Z-score.
* **Excel-støtte:** Leser `.xlsx`-filer (forventer kolonner `Date5`, `Time6` og `ch1`).

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

| Flagg | Beskrivelse | Eksempel |
| :--- | :--- | :--- |
| `--files` | **Påkrevd.** Liste over filer og alias. Format: `Alias=Filsti` | `--files B=Baro.xlsx V=Vann.xlsx` |
| `--formel` | **Påkrevd.** Matematisk formel som bruker aliasene. | `--formel "V.ch1 - B.ch1"` |
| `--clean` | Fjerner støy (Z-score). Standard er 3.0 hvis tall utelates. | `--clean` eller `--clean 4.0` |
| `--tittel` | Setter overskrift på plottet. | `--tittel "Justert Vannstand"` |
| `--help` | Viser hjelpetekst. | `--help` |

---

## Eksempler

### 1. Enkel Barometrisk Kompensasjon
Her laster vi inn `Baro.xlsx` (som **B**) og `Laksemyra.xlsx` (som **L**), og trekker lufttrykket fra vannstanden.

```bash
poetry run sensorplot \
  --files B=Baro.xlsx L="Laksemyra 1.xlsx" \
  --formel "L.ch1 - B.ch1" \
  --tittel "Vannstand korrigert for lufttrykk"
```

### 2. Avansert formel med enhetskonvertering
Hvis barometeret er i kPa og vannstanden i meter, kan vi dele barometeret på 9.81 (tyngdekraft/tetthet) i formelen.

```bash
poetry run sensorplot \
  --files Luft=Baro.xlsx Vann=Laksemyra.xlsx \
  --formel "Vann.ch1 - (Luft.ch1 / 9.81)"
```

### 3. Fjerne støy (Cleaning)
Hvis sensoren har logget feilverdier (f.eks. store hopp), kan du bruke `--clean`. Dette fjerner verdier som avviker mer enn 3 standardavvik fra snittet (default).

```bash
poetry run sensorplot \
  --files Data=MinFil.xlsx \
  --formel "Data.ch1" \
  --clean
```
*(Du kan også spesifisere strenghetsgrad: `--clean 5` beholder mer data, `--clean 2` fjerner mer).*

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

Hvis disse mangler, vil `pytest` hoppe over testene som krever filinnlesing, men fortsatt sjekke logikken i programmet.