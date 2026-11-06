"""Step 3: DenseNet121 transfer learning for pneumonia classification."""
import json
import os
import numpy as np
import torch
import torch.nn as nn
from torchvision.models import densenet121, DenseNet121_Weights
from sklearn.metrics import roc_auc_score, confusion_matrix, roc_curve

from ml.dataset import CXRDataset


def build_model():
    """DenseNet121 pretrained on ImageNet, with the last layer swapped for 1 output.

    Transfer learning: early layers already detect edges and textures that help
    on X-rays too, so we need far less data and training time than from scratch.
    One logit output because the task is binary (pneumonia or not).
    """
    m = densenet121(weights=DenseNet121_Weights.DEFAULT)
    m.classifier = nn.Linear(m.classifier.in_features, 1)
    return m


@torch.no_grad()
def predict(model, loader, device):
    """Return (probabilities, labels) for a whole loader."""
    model.eval()
    probs, ys = [], []
    for x, y in loader:
        with torch.autocast(device_type="cuda", enabled=device == "cuda"):
            logits = model(x.to(device)).squeeze(1)
        probs.append(torch.sigmoid(logits).float().cpu())
        ys.append(y)
    return torch.cat(probs).numpy(), torch.cat(ys).numpy()


def train(split_dir="data/splits", img_dir="data/processed", out_dir="/content/drive/MyDrive/medai_ckpt",
          epochs=6, batch_size=64, lr=1e-4):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    os.makedirs(out_dir, exist_ok=True)

    tr = CXRDataset(f"{split_dir}/train.csv", img_dir, train=True)
    va = CXRDataset(f"{split_dir}/val.csv", img_dir)
    te = CXRDataset(f"{split_dir}/test.csv", img_dir)
    mk = lambda ds, sh: torch.utils.data.DataLoader(ds, batch_size=batch_size, shuffle=sh, num_workers=2, pin_memory=True)
    tl, vl, tel = mk(tr, True), mk(va, False), mk(te, False)

    model = build_model().to(device)

    # Only 22.5% of images are pneumonia. pos_weight makes each positive count
    # about 3.4x more, so the model cannot win by always predicting "normal".
    pos = tr.df.Target.sum()
    pos_weight = torch.tensor([(len(tr.df) - pos) / pos], device=device)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)  # smoothly lowers lr
    scaler = torch.cuda.amp.GradScaler(enabled=device == "cuda")           # mixed precision: faster, less memory

    best = 0.0
    ckpt = os.path.join(out_dir, "best.pt")
    for ep in range(epochs):
        model.train()
        total = 0.0
        for x, y in tl:
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            with torch.autocast(device_type="cuda", enabled=device == "cuda"):
                loss = loss_fn(model(x).squeeze(1), y)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            total += loss.item() * len(x)
        sched.step()
        p, t = predict(model, vl, device)
        auc = roc_auc_score(t, p)
        print(f"epoch {ep+1}/{epochs} train_loss={total/len(tr):.4f} val_AUROC={auc:.4f}")
        if auc > best:  # keep the checkpoint that generalizes best, not the last one
            best = auc
            torch.save(model.state_dict(), ckpt)

    # ----- final evaluation on the untouched test set -----
    model.load_state_dict(torch.load(ckpt, map_location=device))
    pv, tv = predict(model, vl, device)
    fpr, tpr, thr = roc_curve(tv, pv)
    threshold = float(thr[np.argmax(tpr - fpr)])  # Youden's J, chosen on VAL only (never on test)
    pt, tt = predict(model, tel, device)
    cm = confusion_matrix(tt, pt >= threshold)
    tn, fp, fn, tp = cm.ravel()
    metrics = {
        "val_auroc": float(best),
        "test_auroc": float(roc_auc_score(tt, pt)),
        "threshold": threshold,
        "sensitivity": float(tp / (tp + fn)),
        "specificity": float(tn / (tn + fp)),
        "confusion_matrix": cm.tolist(),
    }
    json.dump(metrics, open(os.path.join(out_dir, "metrics.json"), "w"), indent=2)
    print(json.dumps(metrics, indent=2))
    return model, metrics
