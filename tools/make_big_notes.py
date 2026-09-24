#!/usr/bin/env python3
import argparse
from pathlib import Path


def make(path, header, target):
    unit = (
        "Lorem ipsum dolor sit amet. Contact: +30 694 123 4567, "
        "john.doe@example.com, AMKA 12039912345, MRN ZXCVB-1234, "
        "URL https://example.org, IP 192.168.1.100.\n"
    )
    blob = (header + "\n") + unit * (target // len(unit) + 10)
    data = blob.encode("utf-8")[: target]
    if data and data[-1] != 10:  # newline
        data = data[:-1] + b"\n"
    with open(path, "wb") as f:
        f.write(data)
    print(path, len(data), "bytes")


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic upload-size fixtures locally.")
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    make(args.output_dir / "note_big_ok.txt", "OK file (~950KB). Should pass engine + server limit.", 950_000)
    make(args.output_dir / "note_big_fail.txt", "FAIL file (~1.2MB). Should trigger 413 body limit.", 1_200_000)


if __name__ == "__main__":
    main()
