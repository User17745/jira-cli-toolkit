from pathlib import Path
import sys
from jsup.cli import main, toolkit_main, jira_main

if __name__ == '__main__':
    if Path(sys.argv[0]).stem == 'jsup':
        main()
    elif Path(sys.argv[0]).stem == 'jira-cli-toolkit':
        toolkit_main()
    else:
        jira_main()
