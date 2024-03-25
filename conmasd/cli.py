import sys
import signal
import logging
import argparse

from .main import Conmasd
from .version import get_version
from .const import PACKAGE_NAME

def main():
    """CLI entrypoint for the conmasd package
    """
    parser = argparse.ArgumentParser(prog=PACKAGE_NAME, usage='conmasd -f config.json', description=PACKAGE_NAME + ': GitHub Action Self-hosted Runner Operator for Docker')
    parser.add_argument('-f', '--file', help='Config file', type=str, required=True)
    parser.add_argument('-v', '--version', help='Get version', action='version', version=PACKAGE_NAME + ": v" + get_version())
    parser.add_argument('--debug', help='Show debug logs', action='store_true')
    args = parser.parse_args()

    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG if args.debug else logging.INFO)

    client = Conmasd()

    signal.signal(signal.SIGINT, client.exit)
    signal.signal(signal.SIGTERM, client.exit)

    client.set_config_from_file(args.file)
    client.run()

if __name__ == "__main__":
    main()
