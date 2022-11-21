import argparse
import os

from src import conf
from src.persistance.storage import Storage


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    Storage.storage_setup()
    Storage.sync_data()
    print('Data saved.')
    Storage.save()
