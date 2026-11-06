"""Step 4: Grad-CAM heatmaps showing which image regions drove the prediction."""
import numpy as np
import torch
import torch.nn.functional as F
from matplotlib import colormaps


def gradcam(model, x):
    """Compute a Grad-CAM heatmap for the pneumonia logit.

    x: tensor (1, 3, H, W). Returns (cam in 0..1 as numpy HxW, probability).

    How it works: take the last convolutional feature maps (7x7x1024). Weight each
    map by how strongly it increases the pneumonia score (its average gradient),
    sum them, keep only positive evidence (ReLU), and upsample to image size.

    We run the DenseNet forward pass manually instead of using module hooks,
    because torchvision's DenseNet applies an in-place ReLU that breaks hooks.
    """
    model.eval()
    x = x.clone().requires_grad_(False)
    with torch.enable_grad():
        feats = model.features(x)                    # (1, 1024, 7, 7)
        feats.retain_grad()                          # keep gradients of this non-leaf tensor
        pooled = F.adaptive_avg_pool2d(F.relu(feats), 1).flatten(1)  # same as DenseNet's own forward
        logit = model.classifier(pooled).squeeze()
        model.zero_grad()
        logit.backward()
    weights = feats.grad.mean(dim=(2, 3), keepdim=True)   # importance of each feature map
    cam = F.relu((weights * feats).sum(dim=1, keepdim=True))
    cam = F.interpolate(cam, size=x.shape[-2:], mode="bilinear", align_corners=False)[0, 0]
    cam = cam.detach().cpu().numpy()
    cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)  # normalize to 0..1
    return cam, float(torch.sigmoid(logit))


def overlay(gray01, cam, alpha=0.4):
    """Blend the heatmap onto the grayscale image. Returns uint8 RGB (H, W, 3)."""
    heat = colormaps["jet"](cam)[..., :3]
    base = np.stack([gray01] * 3, axis=-1)
    out = (1 - alpha) * base + alpha * heat
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)
