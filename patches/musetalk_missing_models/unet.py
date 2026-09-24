from __future__ import annotations

import json
import math

import torch
import torch.nn as nn
from diffusers import UNet2DConditionModel


class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int = 384, max_len: int = 5000):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x):
        return x + self.pe[:, : x.size(1), :].to(x.device, dtype=x.dtype)


class UNet:
    def __init__(self, unet_config, model_path, use_float16=False, device=None):
        with open(unet_config) as handle:
            config = json.load(handle)
        self.model = UNet2DConditionModel(**config)
        self.pe = PositionalEncoding(d_model=384)
        self.device = device or torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        # Legacy checkpoint objects require weights_only=False on PyTorch 2.6+.
        # Always deserialize on CPU, then move the initialized module to MPS/CUDA.
        weights = torch.load(model_path, map_location="cpu", weights_only=False)
        self.model.load_state_dict(weights)
        if use_float16:
            self.model = self.model.half()
        self.model.to(self.device)
