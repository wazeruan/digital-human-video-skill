from __future__ import annotations

import cv2
import numpy as np
import torch
import torchvision.transforms as transforms
from diffusers import AutoencoderKL


class VAE:
    def __init__(
        self,
        model_path="./models/sd-vae-ft-mse/",
        resized_img=256,
        use_float16=False,
    ):
        self.model_path = model_path
        self.vae = AutoencoderKL.from_pretrained(self.model_path)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.vae.to(self.device)
        if use_float16:
            self.vae = self.vae.half()
        self.scaling_factor = self.vae.config.scaling_factor
        self.transform = transforms.Normalize(
            mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]
        )
        self._resized_img = resized_img
        self._mask_tensor = self.get_mask_tensor()

    def get_mask_tensor(self):
        mask = torch.zeros((self._resized_img, self._resized_img))
        mask[: self._resized_img // 2, :] = 1
        return mask

    def preprocess_img(self, image, half_mask=False):
        if isinstance(image, str):
            image = cv2.imread(image)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = cv2.resize(
            image,
            (self._resized_img, self._resized_img),
            interpolation=cv2.INTER_LANCZOS4,
        )
        tensor = torch.from_numpy(np.asarray(image) / 255.0).float()
        tensor = tensor.permute(2, 0, 1)
        if half_mask:
            tensor = tensor * self._mask_tensor
        tensor = self.transform(tensor).unsqueeze(0)
        return tensor.to(self.vae.device, dtype=self.vae.dtype)

    def encode_latents(self, image):
        with torch.no_grad():
            distribution = self.vae.encode(image.to(self.vae.dtype)).latent_dist
        return self.scaling_factor * distribution.sample()

    def decode_latents(self, latents):
        latents = latents / self.scaling_factor
        image = self.vae.decode(latents.to(self.vae.dtype)).sample
        image = (image / 2 + 0.5).clamp(0, 1)
        image = image.detach().cpu().permute(0, 2, 3, 1).float().numpy()
        return (image * 255).round().astype("uint8")[..., ::-1]

    def get_latents_for_unet(self, image):
        masked = self.encode_latents(self.preprocess_img(image, half_mask=True))
        reference = self.encode_latents(self.preprocess_img(image, half_mask=False))
        return torch.cat([masked, reference], dim=1)
