#!/usr/bin/env python3
"""
Prattyp CLI
"""

import sys
from src import process


def main():
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = input("Введите текст: ")

    result = process(text)
    print(result)


if __name__ == "__main__":
    main()
