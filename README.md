# Sensorplot

**Sensorplot** er et kommandolinjeverktøy (CLI) skrevet i Python for å visualisere og analysere tidsseriedata fra sensorer (Excel-filer).

Verktøyet er designet for å enkelt sammenligne data fra ulike filer, utføre matematiske korrigeringer (f.eks. barometrisk kompensasjon) og automatisk rense data for støy. Det er fleksibelt og kan lese filer med ulike kolonnenavn.

## Funksjonalitet

* **Tidssynkronisering:** Slår automatisk sammen flere datasett basert på nærmeste tidspunkt (håndterer ulik samplingsrate).
* **Matematiske formler:** Lar deg definere regnestykker direkte i terminalen (f.eks. `Vann.ch1 - Baro.ch1`).
* **Automatisk vasking:** Fjerner "outliers" (ekstreme verdier/støy) basert på statistisk Z-score.
* **Fleksibel import:** Støtter egendefinerte kolonnenavn for dato, tid og data.

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
| `--clean` | Fjerner støy (Z-score). Bruk alene eller med tall (f.eks 4.0). | 3.0 (hvis flagg er satt) |
| `--tittel` | Setter overskrift på plottet. | "Sensor Plot" |
| `--datecol` | Navn på kolonnen som inneholder dato. | "Date5" |
| `--timecol` | Navn på kolonnen som inneholder tid. Sett til `None` hvis dato/tid er i én kolonne. | "Time6" |
| `--datacol` | Navn på datakolonnen du vil lese fra filen. | "ch1" |

> **VIKTIG OM FORMELER:**
> Selv om du leser data fra en kolonne som heter "Temperatur" (via `--datacol`), vil programmet internt kalle denne `Alias.ch1` for å gjøre formelskriving enklere.
>
> **Riktig:** `--formel "A.ch1 - B.ch1"`
> **Feil:** `--formel "A.Temperatur - B.Trykk"`

---

## Eksempler

### 1. Standard bruk (Dine faste filer)
Her laster vi inn `Baro.xlsx` og `Laksemyra.xlsx`. Siden vi ikke spesifiserer kolonnenavn, brukes standardene (`Date5`, `Time6`, `ch1`).

```bash
poetry run sensorplot \
  --files B=Baro.xlsx L="Laksemyra 1.xlsx" \
  --formel "L.ch1 - B.ch1" \
  --tittel "Vannstand korrigert for lufttrykk"
```

### 2. Fjerne støy (Cleaning)
Hvis sensoren har logget feilverdier, bruk `--clean`.

```bash
poetry run sensorplot \
  --files Data=MinFil.xlsx \
  --formel "Data.ch1" \
  --clean
```

### 3. Egendefinerte kolonnenavn
Hvis du har en fil med norske kolonnenavn: `Dato`, `Klokkeslett` og `Nivå`.

```bash
poetry run sensorplot \
  --files MinFil=Data.xlsx \
  --formel "MinFil.ch1" \
  --datecol Dato \
  --timecol Klokkeslett \
  --datacol Nivå
```

### 4. Dato og tid i samme kolonne
Hvis filen har en kolonne `Timestamp` som inneholder både dato og tid (f.eks "2024-01-01 12:00").

```bash
poetry run sensorplot \
  --files A=Logg.xlsx \
  --formel "A.ch1" \
  --datecol Timestamp \
  --timecol None
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