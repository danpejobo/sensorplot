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