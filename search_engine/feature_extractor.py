import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image
import numpy as np
from typing import Optional, List, Tuple
import logging
from .data_utils import ImageDataset, collate_fn_skip_none
from torch.utils.data import DataLoader
from torchvision.models import vit_b_16, ViT_B_16_Weights

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageFeatureExtractor:
    """Trích xuất vector đặc trưng ảnh sử dụng ViT."""

    def __init__(self, device: Optional[str] = None):
        """
        Khởi tạo Feature Extractor.

        Args:
            device (Optional[str]): Thiết bị mong muốn ('cuda', 'cpu'). Mặc định tự phát hiện.
        """
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device

        logger.info(f"Sử dụng thiết bị: {self.device}")

        # Khởi tạo mô hình ViT với trọng số đã huấn luyện
        weights = ViT_B_16_Weights.IMAGENET1K_V1
        self.model = vit_b_16(weights=weights)

        # Lưu forward gốc và thay thế bằng hàm lấy đặc trưng
        self._original_forward = self.model.heads # Lưu phần head gốc (thường là lớp Linear)
        self.model.heads = torch.nn.Identity() # Thay thế head bằng lớp Identity để lấy output của encoder

        self.model.eval()
        self.model.to(self.device)

        # Lấy feature_dim từ output của lớp nn.Identity() sau encoder
        # Tạo một ảnh dummy để lấy kích thước output
        dummy_input = torch.randn(1, 3, 224, 224).to(self.device)
        with torch.no_grad():
            dummy_output = self.model(dummy_input)
        self.feature_dim = dummy_output.shape[-1] # 768 cho vit_b_16

        # Pipeline biến đổi ảnh chuẩn của ViT
        self.transform = weights.transforms()

        logger.info(f"Khởi tạo trích xuất đặc trưng ViT với vector đầu ra có chiều: {self.feature_dim}")

    @torch.no_grad()
    def extract_features(self, image_source: str) -> Optional[np.ndarray]:
        """
        Trích xuất vector đặc trưng từ 1 ảnh duy nhất (URL hoặc path).

        Args:
            image_source (str): Đường dẫn file hoặc URL ảnh.

        Returns:
            Optional[np.ndarray]: Vector đặc trưng L2-normalized hoặc None nếu lỗi.
        """
        try:
            # Tải ảnh và áp dụng transform
            image = ImageDataset(image_sources=[image_source], transform=self.transform)[0][0]
            if image is None: # Lỗi đã xảy ra trong __getitem__
                return None

            image_batch = image.unsqueeze(0).to(self.device) # Thêm chiều batch

            # Trích xuất đặc trưng
            features = self.model(image_batch)

            # Chuyển về numpy, bỏ chiều batch
            features = features.cpu().numpy().squeeze()

            # Chuẩn hóa L2
            norm = np.linalg.norm(features)
            if norm > 0:
                features = features / norm
            else:
                logger.warning(f"Vector đặc trưng có norm bằng 0 cho ảnh: {image_source}")

            # Kiểm tra lại kích thước (đề phòng)
            if features.shape != (self.feature_dim,):
                logger.error(f"Kích thước vector không đúng sau trích xuất: {features.shape} cho ảnh {image_source}")
                return None

            return features

        except Exception as e:
            logger.error(f"Lỗi khi trích xuất đặc trưng từ ảnh {image_source}: {e}")
            return None

    @torch.no_grad()
    def extract_features_batch(self, image_sources: List[str], batch_size: int = 32) -> Tuple[List[np.ndarray], List[str]]:
        """
        Trích xuất vector đặc trưng từ một danh sách ảnh (URL hoặc path) theo batch.

        Args:
            image_sources (List[str]): Danh sách đường dẫn file hoặc URL ảnh.
            batch_size (int): Kích thước batch xử lý.

        Returns:
            Tuple[List[np.ndarray], List[str]]:
                - Danh sách các vector đặc trưng L2-normalized.
                - Danh sách các nguồn ảnh tương ứng với vector đặc trưng (đã loại bỏ ảnh lỗi).
        """
        dataset = ImageDataset(image_sources, self.transform)
        # Sử dụng hàm collate_fn_skip_none từ utils.data_utils
        dataloader = DataLoader(
            dataset, 
            batch_size=batch_size, 
            shuffle=False, 
            num_workers=4, 
            collate_fn=collate_fn_skip_none, 
            pin_memory=True if self.device == 'cuda' else False
        )

        all_features = []
        successful_sources = []

        logger.info(f"Bắt đầu trích xuất đặc trưng cho {len(image_sources)} ảnh với batch size {batch_size}...")
        processed_count = 0
        for images_batch, sources_batch in dataloader:
            if images_batch is None: # Batch rỗng do lỗi
                processed_count += batch_size # Ước lượng số lượng đã xử lý
                logger.warning(f"Batch bị bỏ qua hoàn toàn do lỗi tải ảnh.")
                continue

            images_batch = images_batch.to(self.device)
            features_batch = self.model(images_batch)
            features_batch = features_batch.cpu().numpy()

            # Chuẩn hóa L2 cho từng vector trong batch
            norms = np.linalg.norm(features_batch, axis=1, keepdims=True)
            # Tránh chia cho 0
            norms[norms == 0] = 1e-10
            features_batch_normalized = features_batch / norms

            all_features.extend(list(features_batch_normalized))
            successful_sources.extend(sources_batch)
            processed_count += len(sources_batch)
            logger.info(f"Đã xử lý {processed_count}/{len(image_sources)} ảnh...")

        logger.info(f"Hoàn thành trích xuất đặc trưng. Tổng số vector: {len(all_features)}.")
        return all_features, successful_sources

    def __del__(self):
        """Khôi phục lại head gốc của mô hình khi đối tượng bị hủy."""
        if hasattr(self, '_original_forward') and hasattr(self.model, 'heads'):
             self.model.heads = self._original_forward
             logger.debug("Khôi phục head gốc của mô hình ViT.")
        # Giải phóng bộ nhớ GPU nếu có thể
        if self.device == 'cuda':
            del self.model
            torch.cuda.empty_cache()
            logger.info("Giải phóng bộ nhớ GPU.") 