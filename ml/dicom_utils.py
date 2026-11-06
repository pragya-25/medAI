"""Helpers for reading DICOM chest X-rays into numpy arrays."""
import numpy as np
import pydicom


def load_dicom(path):
    """Read a .dcm file and return (pixel_array_as_float32_in_0_1, metadata_dict)."""
    ds = pydicom.dcmread(path)  # parse header tags + pixel data
    img = ds.pixel_array.astype(np.float32)

    # Some X-rays are stored "inverted": MONOCHROME1 means low value = white.
    # We standardize to MONOCHROME2 (low = black) so every image looks alike.
    if getattr(ds, "PhotometricInterpretation", "") == "MONOCHROME1":
        img = img.max() - img

    # Scale to 0..1 so the model sees consistent ranges.
    img = (img - img.min()) / (img.max() - img.min() + 1e-8)

    # Keep only non-identifying, useful tags (privacy: avoid copying PatientName etc.).
    meta = {
        "PatientID": str(getattr(ds, "PatientID", "")),
        "Modality": str(getattr(ds, "Modality", "")),
        "BodyPartExamined": str(getattr(ds, "BodyPartExamined", "")),
        "ViewPosition": str(getattr(ds, "ViewPosition", "")),
        "PatientSex": str(getattr(ds, "PatientSex", "")),
        "PatientAge": str(getattr(ds, "PatientAge", "")),
        "Rows": int(ds.Rows),
        "Columns": int(ds.Columns),
    }
    return img, meta
