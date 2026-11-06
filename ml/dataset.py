"""Step 2: patient-level splits, one-time preprocessing, and a PyTorch Dataset with augmentation."""
import os
import numpy as np
import pandas as pd
import torch
from PIL import Image
from sklearn.model_selection import train_test_split
from monai.transforms import Compose, RandRotate, RandZoom, RandAdjustContrast, ToTensor

from ml.dicom_utils import load_dicom

IMG_SIZE = 224  # DenseNet/EfficientNet were pretrained at about this size


def build_splits(labels_csv, out_dir, seed=42):
    """Collapse box-level rows to one label per patient, then split 70/15/15.

    Splitting by patient (not by image) prevents leakage: the same person
    never appears in both train and test, which would inflate accuracy.
    """
    df = pd.read_csv(labels_csv)
    pat = df.groupby("patientId")["Target"].max().reset_index()
    # stratify keeps the pneumonia/normal ratio equal in each split
    train, rest = train_test_split(pat, test_size=0.30, stratify=pat.Target, random_state=seed)
    val, test = train_test_split(rest, test_size=0.50, stratify=rest.Target, random_state=seed)
    os.makedirs(out_dir, exist_ok=True)
    for name, part in [("train", train), ("val", val), ("test", test)]:
        part.to_csv(os.path.join(out_dir, f"{name}.csv"), index=False)
        print(name, len(part), "pneumonia rate:", round(part.Target.mean(), 3))


def preprocess_all(dcm_dir, patient_ids, out_dir, size=IMG_SIZE):
    """Convert each DICOM to a small 8-bit PNG once, so training reads fast.

    Decoding full 1024x1024 DICOMs every epoch would make the GPU wait on the CPU.
    """
    os.makedirs(out_dir, exist_ok=True)
    for pid in patient_ids:
        dst = os.path.join(out_dir, f"{pid}.png")
        if os.path.exists(dst):  # resumable if Colab disconnects
            continue
        img, _ = load_dicom(os.path.join(dcm_dir, f"{pid}.dcm"))
        im = Image.fromarray((img * 255).astype(np.uint8)).resize((size, size), Image.BILINEAR)
        im.save(dst)


def get_transforms(train):
    """Augmentation applies to training only; val/test must stay untouched.

    No horizontal flip: in chest X-rays the heart is on the left, so flipping
    creates anatomy that does not exist in real patients.
    """
    if not train:
        return Compose([ToTensor()])
    return Compose([
        ToTensor(),
        RandRotate(range_x=0.17, prob=0.5),          # about +/-10 degrees
        RandZoom(min_zoom=0.9, max_zoom=1.1, prob=0.5),
        RandAdjustContrast(gamma=(0.8, 1.2), prob=0.5),  # different scanner exposure
    ])


class CXRDataset(torch.utils.data.Dataset):
    MEAN, STD = 0.485, 0.229  # ImageNet statistics, required by pretrained weights

    def __init__(self, split_csv, img_dir, train=False):
        self.df = pd.read_csv(split_csv)
        self.img_dir = img_dir
        self.tf = get_transforms(train)

    def __len__(self):
        return len(self.df)

    def __getitem__(self, i):
        row = self.df.iloc[i]
        img = np.array(Image.open(os.path.join(self.img_dir, f"{row.patientId}.png")), dtype=np.float32) / 255.0
        x = self.tf(img[None])                    # add channel dim: (1, H, W)
        x = (x - self.MEAN) / self.STD            # normalize
        x = x.repeat(3, 1, 1)                     # pretrained nets expect 3 channels
        return x.float(), torch.tensor(row.Target, dtype=torch.float32)
