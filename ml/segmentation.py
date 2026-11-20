"""Step 3b: 3D U-Net (MONAI) for spleen segmentation, Medical Segmentation Decathlon Task09_Spleen.

Run on Colab (T4 GPU). Used by notebooks/05_segmentation.ipynb.
FOR EDUCATION ONLY. NOT FOR CLINICAL USE.
"""
import json
import os

import numpy as np
import torch
from monai.apps import DecathlonDataset
from monai.data import DataLoader, decollate_batch
from monai.inferers import sliding_window_inference
from monai.losses import DiceLoss
from monai.metrics import DiceMetric
from monai.networks.layers import Norm
from monai.networks.nets import UNet
from monai.transforms import (
    AsDiscrete, Compose, CropForegroundd, EnsureChannelFirstd, EnsureTyped, LoadImaged,
    Orientationd, RandCropByPosNegLabeld, RandFlipd, RandShiftIntensityd, ScaleIntensityRanged, Spacingd,
)
from monai.utils import set_determinism

ROI = (96, 96, 96)  # patch size the network sees at once (3D patches fit in GPU memory; whole CTs do not)
TASK = "Task09_Spleen"


def get_transforms(train):
    """Preprocessing shared by train and validation, plus random patch sampling/augmentation for train only."""
    base = [
        LoadImaged(keys=["image", "label"]),                 # read NIfTI volumes
        EnsureChannelFirstd(keys=["image", "label"]),        # (C, X, Y, Z)
        Orientationd(keys=["image", "label"], axcodes="RAS"),  # same anatomical orientation for every scan
        # Resample to a common voxel size so "1 voxel" means the same distance in every patient.
        Spacingd(keys=["image", "label"], pixdim=(1.5, 1.5, 2.0), mode=("bilinear", "nearest")),
        # CT intensities are in Hounsfield units. This window (-57..164) shows soft tissue where the spleen is.
        ScaleIntensityRanged(keys=["image"], a_min=-57, a_max=164, b_min=0.0, b_max=1.0, clip=True),
        CropForegroundd(keys=["image", "label"], source_key="image"),  # drop empty air around the body
    ]
    if train:
        base += [
            # 4 random 96^3 patches per scan; pos=neg=1 samples spleen and background patches equally.
            RandCropByPosNegLabeld(keys=["image", "label"], label_key="label", spatial_size=ROI,
                                   pos=1, neg=1, num_samples=4, image_key="image", image_threshold=0),
            RandFlipd(keys=["image", "label"], spatial_axis=0, prob=0.3),
            RandShiftIntensityd(keys=["image"], offsets=0.1, prob=0.5),
        ]
    base.append(EnsureTyped(keys=["image", "label"]))
    return Compose(base)


def make_datasets(root="/content/msd", cache_rate=1.0, num_workers=2):
    """Downloads the dataset on first use (about 1.5 GB). Splits the 41 labelled scans into train / validation."""
    kw = dict(root_dir=root, task=TASK, download=True, seed=0, val_frac=0.2,
              cache_rate=cache_rate, num_workers=num_workers)
    train_ds = DecathlonDataset(section="training", transform=get_transforms(True), **kw)
    val_ds = DecathlonDataset(section="validation", transform=get_transforms(False), **kw)
    return train_ds, val_ds


def build_model():
    """3D U-Net: encoder-decoder with skip connections. 2 output channels = background and spleen."""
    return UNet(spatial_dims=3, in_channels=1, out_channels=2,
                channels=(16, 32, 64, 128, 256), strides=(2, 2, 2, 2),
                num_res_units=2, norm=Norm.BATCH)


post_pred = Compose([AsDiscrete(argmax=True, to_onehot=2)])
post_label = Compose([AsDiscrete(to_onehot=2)])


@torch.no_grad()
def predict_volume(model, image, device):
    """Whole-volume prediction by sliding a 96^3 window across the scan and stitching the results."""
    with torch.autocast(device_type="cuda", enabled=device == "cuda"):
        return sliding_window_inference(image.to(device), ROI, 4, model)


@torch.no_grad()
def evaluate(model, val_loader, device):
    """Per-scan Dice on the validation scans. Returns (list of Dice values, mean)."""
    model.eval()
    metric = DiceMetric(include_background=False, reduction="none")
    scores = []
    for batch in val_loader:
        out = [post_pred(i) for i in decollate_batch(predict_volume(model, batch["image"], device))]
        lab = [post_label(i) for i in decollate_batch(batch["label"].to(device))]
        metric(y_pred=out, y=lab)
        scores.append(float(metric.aggregate().flatten()[-1]))
        metric.reset()
    return scores, float(np.mean(scores))


def train(root="/content/msd", out_dir="/content/drive/MyDrive/medai_seg", epochs=100, val_every=5, lr=1e-4):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    os.makedirs(out_dir, exist_ok=True)
    set_determinism(seed=0)

    train_ds, val_ds = make_datasets(root)
    train_loader = DataLoader(train_ds, batch_size=2, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_ds, batch_size=1, num_workers=2)
    print(f"train scans: {len(train_ds)} | validation scans: {len(val_ds)}")

    model = build_model().to(device)
    loss_fn = DiceLoss(to_onehot_y=True, softmax=True)  # Dice loss handles the tiny spleen vs huge background imbalance
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-5)
    scaler = torch.cuda.amp.GradScaler(enabled=device == "cuda")

    best, history, ckpt = -1.0, [], os.path.join(out_dir, "best_unet.pt")
    for ep in range(1, epochs + 1):
        model.train()
        total, steps = 0.0, 0
        for batch in train_loader:
            x, y = batch["image"].to(device), batch["label"].to(device)
            opt.zero_grad()
            with torch.autocast(device_type="cuda", enabled=device == "cuda"):
                loss = loss_fn(model(x), y)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            total += loss.item()
            steps += 1
        rec = {"epoch": ep, "train_loss": total / steps}
        if ep % val_every == 0 or ep == epochs:
            _, mean_dice = evaluate(model, val_loader, device)
            rec["val_dice"] = mean_dice
            if mean_dice > best:
                best = mean_dice
                torch.save(model.state_dict(), ckpt)  # keep the best checkpoint, not the last
        history.append(rec)
        print(rec)

    # Final per-scan numbers from the best checkpoint
    model.load_state_dict(torch.load(ckpt, map_location=device))
    scores, mean_dice = evaluate(model, val_loader, device)
    result = {
        "task": TASK, "epochs": epochs, "train_scans": len(train_ds), "val_scans": len(val_ds),
        "best_val_dice": best, "mean_val_dice": mean_dice,
        "min_val_dice": float(np.min(scores)), "max_val_dice": float(np.max(scores)),
        "per_scan_dice": scores, "history": history,
    }
    with open(os.path.join(out_dir, "seg_metrics.json"), "w") as f:
        json.dump(result, f, indent=2)
    print(f"mean validation Dice = {mean_dice:.3f} (min {np.min(scores):.3f}, max {np.max(scores):.3f})")
    return model, val_ds, result


def show_predictions(model, val_ds, out_png, n=3, device="cuda"):
    """Save a figure: CT slice | ground truth | prediction, for n validation scans (slice with the most spleen)."""
    import matplotlib.pyplot as plt

    model.eval()
    fig, axs = plt.subplots(n, 3, figsize=(12, 4 * n))
    for r in range(n):
        item = val_ds[r]
        img, lab = item["image"][None], item["label"][None]
        pred = predict_volume(model, img, device).argmax(dim=1)[0].cpu().numpy()
        img, lab = img[0, 0].numpy(), lab[0, 0].numpy()
        z = int(np.argmax(lab.sum(axis=(0, 1))))       # slice where the spleen is largest
        inter = ((pred > 0) & (lab > 0)).sum()
        dice = 2 * inter / ((pred > 0).sum() + (lab > 0).sum() + 1e-8)
        for c, (title, mask) in enumerate([("CT slice", None), ("Ground truth", lab[:, :, z]), (f"Prediction (Dice {dice:.2f})", pred[:, :, z])]):
            axs[r, c].imshow(np.rot90(img[:, :, z]), cmap="gray")
            if mask is not None:
                axs[r, c].imshow(np.ma.masked_where(np.rot90(mask) == 0, np.rot90(mask)), cmap="autumn", alpha=0.6)
            axs[r, c].set_title(title)
            axs[r, c].axis("off")
    plt.tight_layout()
    plt.savefig(out_png, dpi=110)
    plt.show()
