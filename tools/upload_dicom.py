"""Upload DICOM files to Orthanc.   Usage: python tools/upload_dicom.py path/to/folder_or_file"""
import os
import sys
import requests

ORTHANC = os.environ.get("ORTHANC_URL", "http://localhost:8042")


def main(path):
    files = [os.path.join(path, f) for f in os.listdir(path)] if os.path.isdir(path) else [path]
    for f in files:
        if not f.lower().endswith(".dcm"):
            continue
        with open(f, "rb") as fh:
            r = requests.post(f"{ORTHANC}/instances", data=fh.read(), headers={"Content-Type": "application/dicom"})
        print(f, "->", r.status_code, r.json().get("Status"))


if __name__ == "__main__":
    main(sys.argv[1])
