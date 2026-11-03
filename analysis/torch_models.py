"""Modele PyTorch (CUDA) do rozpoznawania użytkownika z wektora cech sesji."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset


def resolve_device(requested: str = "auto") -> torch.device:
    requested = (requested or "auto").lower()
    if requested == "cpu":
        return torch.device("cpu")
    if requested == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("Żądano CUDA, ale torch.cuda.is_available() == False")
        return torch.device("cuda")
    # auto
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def describe_device(device: torch.device) -> str:
    if device.type == "cuda":
        idx = device.index or 0
        name = torch.cuda.get_device_name(idx)
        mem = torch.cuda.get_device_properties(idx).total_memory / (1024**3)
        return f"cuda:{idx} ({name}, {mem:.1f} GiB)"
    return "cpu"


class KeystrokeMLP(nn.Module):
    def __init__(self, n_features: int, n_classes: int, hidden: int = 128, dropout: float = 0.2):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_features, hidden),
            nn.ReLU(),
            nn.BatchNorm1d(hidden),
            nn.Dropout(dropout),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.BatchNorm1d(hidden),
            nn.Dropout(dropout),
            nn.Linear(hidden, n_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


@dataclass
class TrainConfig:
    epochs: int = 80
    batch_size: int = 32
    lr: float = 1e-3
    weight_decay: float = 1e-4
    hidden: int = 128
    dropout: float = 0.2


class TorchMLPClassifier:
    """Interfejs zbliżony do sklearn: fit / predict."""

    def __init__(self, device: torch.device, cfg: TrainConfig | None = None):
        self.device = device
        self.cfg = cfg or TrainConfig()
        self.model: KeystrokeMLP | None = None
        self.mean_: np.ndarray | None = None
        self.std_: np.ndarray | None = None
        self.n_classes_: int = 0

    def _scale(self, X: np.ndarray, fit: bool = False) -> np.ndarray:
        if fit:
            self.mean_ = X.mean(axis=0)
            self.std_ = X.std(axis=0)
            self.std_[self.std_ < 1e-8] = 1.0
        assert self.mean_ is not None and self.std_ is not None
        return (X - self.mean_) / self.std_

    def fit(self, X: np.ndarray, y: np.ndarray) -> TorchMLPClassifier:
        X = np.asarray(X, dtype=np.float32)
        y = np.asarray(y, dtype=np.int64)
        Xs = self._scale(X, fit=True)
        self.n_classes_ = int(y.max()) + 1

        self.model = KeystrokeMLP(
            n_features=Xs.shape[1],
            n_classes=self.n_classes_,
            hidden=self.cfg.hidden,
            dropout=self.cfg.dropout,
        ).to(self.device)

        ds = TensorDataset(torch.from_numpy(Xs), torch.from_numpy(y))
        loader = DataLoader(ds, batch_size=min(self.cfg.batch_size, len(ds)), shuffle=True)

        opt = torch.optim.AdamW(self.model.parameters(), lr=self.cfg.lr, weight_decay=self.cfg.weight_decay)
        loss_fn = nn.CrossEntropyLoss()

        self.model.train()
        for _ in range(self.cfg.epochs):
            for xb, yb in loader:
                xb = xb.to(self.device)
                yb = yb.to(self.device)
                opt.zero_grad(set_to_none=True)
                logits = self.model(xb)
                loss = loss_fn(logits, yb)
                loss.backward()
                opt.step()
        return self

    @torch.inference_mode()
    def predict(self, X: np.ndarray) -> np.ndarray:
        assert self.model is not None
        X = np.asarray(X, dtype=np.float32)
        Xs = self._scale(X, fit=False)
        self.model.eval()
        xb = torch.from_numpy(Xs).to(self.device)
        logits = self.model(xb)
        return logits.argmax(dim=1).cpu().numpy()
