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

Du kan kjøre verktøyet ved å bruke `poetry run sensorplot`.

### Syntaks
```bash
poetry run sensorplot --files <ALIAS>=<FILSTI> ... --formel "<FORMEL>" [OPTIONS]