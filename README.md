# Sensorplot

**Sensorplot** er et kommandolinjeverktøy (CLI) skrevet i Python for å visualisere og analysere tidsseriedata fra sensorer (Excel-filer).

Verktøyet er designet for å enkelt sammenligne data fra ulike filer, utføre matematiske korrigeringer (f.eks. barometrisk kompensasjon) og automatisk rense data for støy. Det støtter både plotting av **flere serier** i samme graf, interaktiv visning (GUI) og lagring til fil.

## Funksjonalitet

* **Tidssynkronisering:** Slår automatisk sammen flere datasett basert på nærmeste tidspunkt (håndterer ulik samplingsrate).
* **Multiseries:** Kan plotte flere linjer i samme figur (f.eks. to ulike sensorer korrigert mot samme barometer).
* **Matematiske formler:** Lar deg definere regnestykker direkte i terminalen (f.eks. `Vann.ch1 - Baro.ch1`).
* **Automatisk vasking:** Fjerner "outliers" (ekstreme verdier/støy) basert på statistisk Z-score.
* **Fleksibel import:** Støtter egendefinerte kolonnenavn for dato, tid og data.
* **Lagring:** Kan lagre plott som bildefil (PNG, PDF) – perfekt for remote servere eller VS Code.

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
poetry run sensorplot --files <ALIAS>=<FILSTI> ... [OPTIONS]
```

### Argumenter

| Flagg | Beskrivelse | Eksempel |
| :--- | :--- | :--- |
| `--files` | **Påkrevd.** Liste over filer og alias. Format: `Alias=Filsti` | `--files L1=Laks1.xlsx B=Baro.xlsx` |
| `--series` | **Anbefalt.** Liste over serier å plotte. Format: `"Navn=Formel"`. | `--series "Nivå 1=L1.ch1 - B.ch1"` |
| `--formel` | Alternativ til `--series` for å plotte kun én enkelt linje. | `--formel "L1.ch1 - B.ch1"` |
| `--clean` | Fjerner støy (Z-score). Bruk alene eller med tall (f.eks 4.0). | `--clean` (std: 3.0) |
| `--output` | Lagring/Visning. Se tabell under for oppførsel. | Vis GUI (default) |
| `--tittel` | Setter overskrift på plottet. | `--tittel "Oversikt"` |
| `--datecol` | Navn på kolonnen som inneholder dato. | Standard: "Date5" |
| `--timecol` | Navn på tidskolonne (`None` hvis samlet). | Standard: "Time6" |
| `--datacol` | Navn på datakolonnen du vil lese fra filen. | Standard: "ch1" |

### Oppførsel for `--output`

| Kommando | Resultat |
| :--- | :--- |
| `sensorplot ...` (ingen flagg) | Åpner et **GUI-vindu** med plottet (lokal bruk). |
| `sensorplot ... --output` | Lagrer plottet som **`sensorplot.png`** i gjeldende mappe. |
| `sensorplot ... --output graf.pdf` | Lagrer plottet som **`graf.pdf`** (valgfritt navn/sti). |

> **VIKTIG OM FORMELER:**
> Uansett hva datakolonnen heter i Excel-filen (f.eks. "Temperatur" eller "Level"), vil programmet internt kalle denne `Alias.ch1`. Bruk alltid `.ch1` i formlene dine.

---

## Eksempler

### 1. Flere serier (Hovedfunksjon)
Her laster vi inn to sensorfiler (`L1`, `L2`) og én barometerfil (`B`). Vi plotter to linjer i samme graf: begge sensorene korrigert mot samme barometer.

```bash
poetry run sensorplot \
  --files L1=Laksemyra1.xlsx L2=Laksemyra2.xlsx B=Baro.xlsx \
  --series "Laksemyra 1=L1.ch1 - B.ch1" "Laksemyra 2=L2.ch1 - B.ch1" \
  --tittel "Sammenligning av lokasjoner"
```

### 2. Enkelt plott (Hurtigbruk)
Hvis du bare skal plotte én ting, kan du bruke `--formel` i stedet for `--series`.

```bash
poetry run sensorplot \
  --files V=Vann.xlsx B=Baro.xlsx \
  --formel "V.ch1 - B.ch1"
```

### 3. Avansert formel (Enhetskonvertering)
Konverter barometer (kPa) til meter vannsøyle (dele på 9.81) før subtraksjon.

```bash
poetry run sensorplot \
  --files V=Vann.xlsx B=Baro.xlsx \
  --series "Justert nivå=V.ch1 - (B.ch1 / 9.81)"
```

### 4. Fjerne støy og lagre til fil (Server)
Fjerner automatisk punkter som er støy (outliers) og lagrer resultatet som et bilde. Nyttig på servere uten skjerm.

```bash
poetry run sensorplot \
  --files D=Data.xlsx \
  --formel "D.ch1" \
  --clean \
  --output plott.png
```

### 5. Egendefinerte kolonnenavn
Hvis filene dine ikke følger standarden (Date5/Time6/ch1).
F.eks hvis kolonnene heter: 'Dato', 'Tid', 'Måling'.

```bash
poetry run sensorplot \
  --files F=Fil.xlsx \
  --formel "F.ch1" \
  --datecol Dato --timecol Tid --datacol Måling
```

### 6. Dato og tid samlet
Hvis dato og tid ligger i samme kolonne (f.eks 'Tidsstempel').

```bash
poetry run sensorplot \
  --files F=Fil.xlsx \
  --formel "F.ch1" \
  --datecol Tidsstempel --timecol None
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