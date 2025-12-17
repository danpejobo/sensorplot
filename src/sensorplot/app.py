import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotly.graph_objects as go
import re
import os
import tempfile
import io
import concurrent.futures
import threading
from pathlib import Path
from datetime import datetime

# Import kjernefunksjonalitet
from sensorplot.core import last_og_rens_data, vask_data, SensorResult

# Lås for å håndtere delt tilgang til fil-cachen i tråder
cache_lock = threading.Lock()


def save_uploaded_file(uploaded_file):
    """Lagrer opplastet fil midlertidig."""
    try:
        suffix = Path(uploaded_file.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            return tmp.name
    except Exception as e:
        st.error(f"Feil ved lagring av fil: {e}")
        return None


def sanitize_filename(title):
    """Gjør om en tittel til et trygt filnavn."""
    clean = re.sub(r'[^\w\s-]', '', title).strip().lower()
    return re.sub(r'[\s]+', '_', clean) + ".png"


def configure_page() -> None:
    st.set_page_config(page_title="Sensorplot GUI",
                       layout="wide", page_icon="📈")


def run_app() -> None:
    st.title("Sensorplot Analyseverktøy 📈")

    plot_title = None
    x_int = None

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("1. Dataflyt")
        uploaded_files = st.file_uploader(
            "Last opp filer (.xlsx / .csv)", accept_multiple_files=True)

        file_registry = {}
        if uploaded_files:
            st.caption("Gi alias til filene:")
            for uf in uploaded_files:
                clean_name = uf.name.split('.')[0].replace(" ", "_")
                c1, c2 = st.columns([0.6, 0.4])
                with c1:
                    st.write(f"📄 {clean_name}")
                with c2:
                    alias = st.text_input(
                        uf.name, value=clean_name, key=f"alias_{uf.name}", label_visibility="collapsed")

                temp_path = save_uploaded_file(uf)
                if temp_path:
                    file_registry[alias] = {'path': temp_path, 'name': uf.name}

        st.divider()
        st.header("2. Konfigurasjon")
        with st.expander("Avanserte kolonnenavn", expanded=False):
            col_date = st.text_input("Dato", value="Date5")
            col_time = st.text_input("Tid", value="Time6")
            col_data = st.text_input("Data", value="ch1")
            if col_time and col_time.lower() == "none":
                col_time = None

    # --- HOVEDVINDU ---
    if file_registry:
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("3. Beregninger")
            formulas_input = st.text_area(
                "Definer formler",
                value="# Eks: Vannstand = L1.ch1 - B.ch1",
                height=180
            )
        with c2:
            st.subheader("4. Visning")
            plot_title = st.text_input("Tittel", value="Sensoranalyse")
            z_score = st.slider("Støyvask (Z-Score)", 1.0, 10.0, 3.0)
            x_int = st.text_input(
                "X-Akse Intervall (for PNG)", placeholder="Eks: 1M, 2W")

        if st.button("🚀 Generer Plott", type="primary", width="stretch"):
            # Her kaller vi den multithreadede funksjonen
            results = calculate_series(
                formulas_input, file_registry, col_date, col_time, col_data, z_score)
            if results:
                st.session_state['sensor_results'] = results
                st.session_state['sensor_title'] = plot_title
                st.session_state['plot_id'] = st.session_state.get(
                    'plot_id', 0) + 1
                st.rerun()
    else:
        st.info("Velkommen! Start med å laste opp sensorfiler.")

    # --- VISNING ---
    if 'sensor_results' in st.session_state:
        current_title = plot_title if plot_title else st.session_state['sensor_title']
        display_results_interface(
            st.session_state['sensor_results'], current_title, x_int)


def _process_single_line(line, file_registry, loaded_dfs, col_date, col_time, col_data, z_score):
    """
    Hjelpefunksjon som kjøres i en egen tråd for hver formel.
    Inneholder nå logikken for dynamiske kolonnenavn.
    """
    if "=" not in line:
        return None

    label, formula = line.split("=", 1)
    label, formula = label.strip(), formula.strip()

    formula = re.sub(r'(\d+),(\d+)', r'\1.\2', formula)

    # --- ENDRING: Dynamisk sjekk for Alias.DittKolonneNavn ---
    safe_col_name = re.escape(col_data)
    pattern_aliases = rf'\b([a-zA-Z0-9_\-æøåÆØÅ]+)\.{safe_col_name}\b'
    needed = re.findall(pattern_aliases, formula)

    if not needed:
        return None

    current_dfs = []

    # Lasting av filer (Thread-safe cache tilgang)
    for alias in needed:
        if alias not in file_registry:
            return {'error': f"Mangler alias: {alias} i formel '{label}'"}

        # Sjekk cache først (med lås for lesing/skriving)
        already_loaded = False
        with cache_lock:
            if alias in loaded_dfs:
                current_dfs.append(loaded_dfs[alias])
                already_loaded = True

        if not already_loaded:
            try:
                # Tung operasjon: Lese fil
                # Bruker lås for å unngå race condition ved lasting
                with cache_lock:
                    if alias not in loaded_dfs:  # Dobbeltsjekk
                        loaded_dfs[alias] = last_og_rens_data(
                            file_registry[alias]['path'], alias, col_date, col_time, col_data
                        )
                    current_dfs.append(loaded_dfs[alias])
            except Exception as e:
                return {'error': f"Feil i fil {alias}: {e}"}

    # Beregning
    try:
        merged = current_dfs[0]
        for o in current_dfs[1:]:
            merged = pd.merge_asof(
                merged, o, on='Datetime', direction='nearest', tolerance=pd.Timedelta('10min'))

        # --- ENDRING: Erstatt Alias.Kolonne med `Alias.Kolonne` (backticks) for eval ---
        safe_f = re.sub(
            rf'\b([a-zA-Z0-9_\-æøåÆØÅ]+\.{safe_col_name})\b', r'`\1`', formula)

        result = merged.eval(safe_f, engine='python')

        if isinstance(result, (tuple, list)):
            return {'error': f"Feil i formel '{label}': Resultat ble liste/tuple."}

        merged['Resultat'] = result
        merged, _ = vask_data(merged, 'Resultat', z_score)

        return {'success': SensorResult(label=label, df=merged)}

    except Exception as e:
        return {'error': f"Beregningfeil '{label}': {e}"}


def calculate_series(formulas_text, file_registry, col_date, col_time, col_data, z_score):
    """Kjører data-prosesseringen parallelt med tråder."""
    lines = [line.strip() for line in formulas_text.split(
        '\n') if line.strip() and not line.strip().startswith("#")]
    if not lines:
        st.warning("Ingen formler definert.")
        return None

    loaded_dfs = {}
    raw_results = []
    errors = []

    with st.spinner("Leser filer og beregner (Multithreaded)..."):
        # Bruk ThreadPoolExecutor for å kjøre linjene parallelt
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Start alle oppgaver
            futures = [
                executor.submit(_process_single_line, line, file_registry,
                                loaded_dfs, col_date, col_time, col_data, z_score)
                for line in lines
            ]

            # Samle resultater etter hvert som de blir ferdige
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                if res:
                    if 'success' in res:
                        raw_results.append(res['success'])
                    elif 'error' in res:
                        errors.append(res['error'])

    # Vis alle feilmeldinger i hovedtråden
    for err in errors:
        st.error(err)

    if raw_results:
        # Konsolidering (Slå sammen serier med samme navn)
        consolidated = {}
        for r in raw_results:
            if r.label not in consolidated:
                consolidated[r.label] = []
            consolidated[r.label].append(r.df)

        final_results = []
        for lbl, dfs in consolidated.items():
            if len(dfs) == 1:
                final_results.append(SensorResult(label=lbl, df=dfs[0]))
            else:
                final_results.append(SensorResult(
                    label=lbl, df=pd.concat(dfs).sort_values('Datetime')))

        # Rydd opp temp filer
        for info in file_registry.values():
            if os.path.exists(info['path']):
                try:
                    os.remove(info['path'])
                except:
                    pass

        return final_results

    return None


def display_results_interface(results, title, x_interval):
    """Viser slider, plot og nedlastingsknapp."""
    all_datetimes = []
    for res in results:
        if not res.df.empty:
            all_datetimes.append(res.df['Datetime'])

    filtered_results = results

    st.divider()

    if all_datetimes:
        full_series = pd.concat(all_datetimes)
        min_dt = full_series.min().to_pydatetime()
        max_dt = full_series.max().to_pydatetime()

        st.subheader("5. Tidsfilter")

        if min_dt == max_dt:
            st.warning("Datagrunnlaget inneholder kun ett tidspunkt.")
        else:
            current_plot_id = st.session_state.get('plot_id', 0)

            val_range = st.slider(
                "Juster tidsvindu:",
                min_value=min_dt,
                max_value=max_dt,
                value=(min_dt, max_dt),
                format="DD.MM.YY HH:mm",
                key=f"time_slider_{current_plot_id}"
            )

            filtered_results = []
            start_filter, end_filter = val_range
            for res in results:
                mask = (res.df['Datetime'] >= start_filter) & (
                    res.df['Datetime'] <= end_filter)
                filtered_df = res.df.loc[mask]
                if not filtered_df.empty:
                    filtered_results.append(SensorResult(
                        label=res.label, df=filtered_df))

    st.subheader("📊 Interaktiv Analyse")
    plot_interactive_plotly(filtered_results, title)

    st.divider()
    col_dl, _ = st.columns([1, 2])
    with col_dl:
        png_buffer = generate_static_matplotlib(
            filtered_results, title, x_interval)
        safe_name = sanitize_filename(title)

        st.download_button(
            label=f"💾 Last ned {safe_name}",
            data=png_buffer,
            file_name=safe_name,
            mime="image/png",
            width="stretch"
        )


def plot_interactive_plotly(results, title):
    fig = go.Figure()
    for serie in results:
        fig.add_trace(go.Scatter(
            x=serie.df['Datetime'], y=serie.df['Resultat'],
            mode='lines', name=serie.label,
            hovertemplate='%{y:.2f}<br>%{x|%d.%m.%Y %H:%M}'
        ))

    fig.update_layout(
        title=title, xaxis_title="Tid", yaxis_title="Verdi",
        hovermode="x unified", legend=dict(orientation="h", y=1.02, x=1),
        margin=dict(l=40, r=40, t=40, b=40), template="plotly_white"
    )

    try:
        st.plotly_chart(fig, width="stretch")
    except TypeError:
        st.plotly_chart(fig, use_container_width=True)


def generate_static_matplotlib(results, title, x_interval):
    fig, ax = plt.subplots(figsize=(14, 7))
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']

    has_data = False
    for i, serie in enumerate(results):
        if not serie.df.empty:
            has_data = True
            farge = colors[i % len(colors)]
            ax.plot(serie.df['Datetime'], serie.df['Resultat'],
                    label=serie.label, color=farge, linewidth=1.5, alpha=0.9)

    ax.set_title(title, fontsize=16)
    ax.set_ylabel("Verdi")

    if has_data:
        locator = None
        if x_interval:
            match = re.match(r'^(\d+)([DWMYdwmy])$', x_interval)
            if match:
                num = int(match.group(1))
                unit = match.group(2).upper()
                if unit == 'D':
                    locator = mdates.DayLocator(interval=num)
                elif unit == 'W':
                    locator = mdates.WeekdayLocator(interval=num)
                elif unit == 'M':
                    locator = mdates.MonthLocator(interval=num)
                elif unit == 'Y':
                    locator = mdates.YearLocator(base=num)
        if not locator:
            locator = mdates.AutoDateLocator()
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
        fig.autofmt_xdate()

    ax.grid(True, alpha=0.3)
    ax.legend()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf


def main() -> None:
    configure_page()
    run_app()


if __name__ == "__main__":
    main()
