"""Loads the trained model and runs prediction + Grad-CAM on one DICOM."""
import io
import json
import os
import sys
import numpy as np
import pydicom
import torch
import torch.nn as nn
from PIL import Image
from torchvision.models import densenet121

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.gradcam import gradcam, overlay  # noqa: E402

MODEL_DIR = os.environ.get("MEDAI_MODEL_DIR", "service/models")
MEAN, STD, SIZE = 0.485, 0.229, 224  # must match training preprocessing exactly


class Predictor:
    def __init__(self):
        self.model = densenet121(weights=None)  # weights come from our checkpoint, no download needed
        self.model.classifier = nn.Linear(self.model.classifier.in_features, 1)
        self.model.load_state_dict(torch.load(os.path.join(MODEL_DIR, "best.pt"), map_location="cpu"))
        self.model.eval()
        with open(os.path.join(MODEL_DIR, "metrics.json")) as f:
            m = json.load(f)
        self.threshold = m["threshold"]          # chosen on the validation set during training
        self.version = f"densenet121-auroc{m['test_auroc']:.3f}"

    @staticmethod
    def _preprocess(dicom_bytes):
        """Same steps as ml/dicom_utils.py + ml/dataset.py: invert MONOCHROME1, scale 0-1, 8-bit, resize, normalize."""
        ds = pydicom.dcmread(io.BytesIO(dicom_bytes))
        img = ds.pixel_array.astype(np.float32)
        if getattr(ds, "PhotometricInterpretation", "") == "MONOCHROME1":
            img = img.max() - img
        img = (img - img.min()) / (img.max() - img.min() + 1e-8)
        im = Image.fromarray((img * 255).astype(np.uint8)).resize((SIZE, SIZE), Image.BILINEAR)
        gray = np.asarray(im, dtype=np.float32) / 255.0
        x = torch.from_numpy((gray - MEAN) / STD).float()[None, None].repeat(1, 3, 1, 1)
        return gray, x

    def run(self, dicom_bytes):
        gray, x = self._preprocess(dicom_bytes)
        cam, prob = gradcam(self.model, x)
        return {
            "probability": prob,
            "predicted_positive": int(prob >= self.threshold),
            "heatmap": overlay(gray, cam),   # uint8 RGB image
            "original": (gray * 255).astype(np.uint8),
        }
