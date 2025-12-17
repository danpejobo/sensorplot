import sys
from pathlib import Path
from streamlit.web import cli as stcli
from sensorplot.cli import main as cli_main

def gui():
    """
    Start-funksjon for GUI.
    Denne fungerer som en wrapper rundt 'streamlit run src/sensorplot/app.py'.
    """
    # Finn stien til app.py relativt til denne filen (__main__.py)
    package_dir = Path(__file__).parent
    app_path = package_dir / "app.py"
    
    # Bygg opp kommandoen som om vi skrev den i terminalen
    # sys.argv[0] er scriptnavnet, vi bytter ut resten
    sys.argv = ["streamlit", "run", str(app_path)] + sys.argv[1:]
    
    # Kjør streamlit
    sys.exit(stcli.main())

def main():
    """
    Standard inngangspunkt når modulen kjøres med 'python -m sensorplot'.
    Vi lar denne peke til CLI som standard.
    """
    cli_main()

if __name__ == "__main__":
    main()