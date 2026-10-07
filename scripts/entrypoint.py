from pathlib import Path
import sys
from jsup.cli import main, toolkit_main

if __name__ == '__main__':
    if Path(sys.argv[0]).stem == 'jsup':
        main()
    else:
        toolkit_main()
