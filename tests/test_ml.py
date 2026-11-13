"""ML tests: Grad-CAM output is well-formed, and inference preprocessing matches training preprocessing."""
import io

import numpy as np
import pydicom
import pytest
import torch
import torch.nn as nn
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid
from torchvision.models import densenet121

from ml.gradcam import gradcam, overlay
from service.inference import Predictor


@pytest.fixture(scope="module")
def tiny_model():
    m = densenet121(weights=None)
    m.classifier = nn.Linear(m.classifier.in_features, 1)
    return m.eval()


def make_dicom_bytes(photometric="MONOCHROME2", size=64):
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.7"
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds = FileDataset(None, {}, file_meta=meta, preamble=b"\0" * 128)
    ds.Rows = ds.Columns = size
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = photometric
    ds.BitsAllocated, ds.BitsStored, ds.HighBit, ds.PixelRepresentation = 8, 8, 7, 0
    ds.PixelData = (np.arange(size * size) % 256).astype(np.uint8).tobytes()
    buf = io.BytesIO()
    ds.save_as(buf)
    return buf.getvalue()


def test_gradcam_shape_range_and_probability(tiny_model):
    cam, prob = gradcam(tiny_model, torch.randn(1, 3, 224, 224))
    assert cam.shape == (224, 224)
    assert 0.0 <= cam.min() and cam.max() <= 1.0
    assert 0.0 <= prob <= 1.0


def test_overlay_is_uint8_rgb():
    out = overlay(np.random.rand(224, 224).astype(np.float32), np.random.rand(224, 224))
    assert out.shape == (224, 224, 3) and out.dtype == np.uint8


def test_preprocess_output_shape_and_normalization():
    gray, x = Predictor._preprocess(make_dicom_bytes())
    assert gray.shape == (224, 224) and 0.0 <= gray.min() and gray.max() <= 1.0
    assert tuple(x.shape) == (1, 3, 224, 224)
    assert torch.allclose(x[0, 0], x[0, 1])  # grayscale replicated to 3 channels


def test_monochrome1_is_inverted():
    g2, _ = Predictor._preprocess(make_dicom_bytes("MONOCHROME2"))
    g1, _ = Predictor._preprocess(make_dicom_bytes("MONOCHROME1"))
    assert np.allclose(g1, 1.0 - g2, atol=0.02)  # inverted polarity is standardized
