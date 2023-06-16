import sys
from streamlit.web import cli as stcli

if __name__ == '__main__':
    sys.argv = ["streamlit", "run", "./01-Home.py"]
    sys.exit(stcli.main())

