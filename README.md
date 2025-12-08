# Sensorplot

**Sensorplot** er et moderne, raskt og fleksibelt kommandolinjeverktøy (CLI) for visualisering og analyse av tidsseriedata. Det støtter både Excel- og CSV-filer, og er optimalisert for å håndtere flere datasett samtidig.

Verktøyet gjør det enkelt å sammenligne sensordata, utføre matematiske korrigeringer (f.eks. barometrisk kompensasjon) og automatisk fjerne støy.

## Funksjonalitet

* **Multiformat-støtte:** Leser både **Excel** (`.xlsx`) og **CSV** (`.csv`) automatisk.
* **Smart CSV-lesing:** Detekterer automatisk start-raden for data i CSV-filer fra loggere (håndterer metadata i toppen) og skiller mellom norsk/internasjonalt format.
* **Konfigurasjon:** Støtter **YAML**-filer for å lagre komplekse oppsett (filer, formler, innstillinger).
* **Parallell prosessering:** Laster og behandler filer samtidig (multithreading) for maksimal ytelse.
* **Multiseries:** Kan plotte flere uavhengige serier i samme graf, eller sy sammen oppdelte filer (f.eks. 2023 + 2024) til én kontinuerlig tidslinje.
* **Matematiske formler:** Definer regnestykker direkte i terminalen eller config (f.eks. `Vann.ch1 - Baro.ch1`).
* **Automatisk vasking:** Fjerner "outliers" (støy) basert på statistisk Z-score.

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
poetry run sensorplot [OPTIONS]
```

### Argumenter

| Flagg | Beskrivelse | Standard |
| :--- | :--- | :--- |
| `--config`, `-c` | **Anbefalt.** Sti til YAML-konfigurasjonsfil. | - |
| `--files` | Liste over filer og alias. Format: `Alias=Filsti` (hvis ikke config brukes). | - |
| `--series` | Liste over serier å plotte. Format: `"Navn=Formel"`. | - |
| `--formel` | Enkel modus for å plotte én serie. | - |
| `--clean` | Fjerner støy (Z-score). Eks: `--clean 3.0`. | 3.0 |
| `--output` | Lagrer plott til fil. Uten filnavn brukes `sensorplot.png`. | Vis GUI |
| `--tittel` | Setter overskrift på plottet. | "Sensor Plot" |
| `--x-interval`| Manuell etikett-intervall på x-akse (eks: `1M`, `2W`, `3D`). | Auto |
| `--datecol` | Navn på kolonnen som inneholder dato. | "Date5" |
| `--timecol` | Navn på tidskolonne (`None` hvis samlet). | "Time6" |
| `--datacol` | Navn på datakolonnen du vil lese fra filen. | "ch1" |

> **VIKTIG:** Argumenter gitt i terminalen (CLI) vil alltid overstyre innstillinger i konfigurasjonsfilen.

---

## Eksempler

### 1. Bruk av konfigurasjonsfil (Anbefalt)
For komplekse plott med mange filer og spesifikke innstillinger, bruk en YAML-fil (se `example_config.yaml`).

```bash
poetry run sensorplot --config min_analyse.yaml
```

### 2. Enkel bruk (CLI)
Her laster vi inn en vannstand-fil (L) og en baro-fil (B) og plotter differansen.

```bash
poetry run sensorplot \
  --files L=Vann.xlsx B=Baro.xlsx \
  --series "Korrigert Vannstand=L.ch1 - B.ch1"
```

### 3. CSV-filer med egne kolonnenavn
Hvis du har CSV-filer fra loggere (som ofte har andre kolonnenavn enn standarden), må du spesifisere hvilke kolonner som skal brukes.

```bash
poetry run sensorplot \
  --files L=Logger.csv \
  --series "Rådata=L.ch1" \
  --datecol Date --timecol Time --datacol LEVEL
```

### 4. Manuell styring av X-akse
Hvis en lang tidsserie gir for tett tekst på x-aksen, kan du tvinge intervallet.

```bash
# Vis en etikett for hver måned
poetry run sensorplot --config oppsett.yaml --x-interval 1M
```

---

## Utvikling og Testing

Prosjektet er bygget med moderne Python-prinsipper (Type Hinting, Dataclasses, Multithreading).

### Kjøre tester
Testene ligger i `tests/`-mappen. For å kjøre dem:

```bash
poetry run pytest
```