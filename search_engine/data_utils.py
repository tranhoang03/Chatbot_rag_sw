import torch
from torch.utils.data import Dataset
from PIL import Image
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from io import BytesIO
import os
import logging
from typing import List, Tuple, Optional
from collections import defaultdict

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Theo dõi số lần lỗi cho mỗi URL
error_counts = defaultdict(int)
MAX_ERRORS = 3  # Số lần thử tối đa cho mỗi URL

def create_session():
    """Tạo session với retry và timeout config."""
    session = requests.Session()
    
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[408, 429, 500, 502, 503, 504],
    )
    
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    return session

http_session = create_session()

def collate_fn_skip_none(batch):
    """
    Collate function cho DataLoader, bỏ qua các sample bị lỗi (img is None).
    """
    batch = [(img, src) for img, src in batch if img is not None]
    if not batch:
        return None, None
    images = torch.stack([item[0] for item in batch])
    sources = [item[1] for item in batch]
    return images, sources

class ImageDataset(Dataset):
    """Dataset xử lý ảnh từ URL hoặc file local."""

    def __init__(self, image_sources: List[str], transform=None):
        if not all(isinstance(src, str) for src in image_sources):
            raise ValueError("Tất cả phần tử trong image_sources phải là string (đường dẫn hoặc URL).")

        self.image_sources = image_sources
        self.transform = transform
        self.failed_sources = []

    def __len__(self):
        return len(self.image_sources)

    def _load_image(self, source: str) -> Image.Image:
        global error_counts

        if not isinstance(source, str):
            raise TypeError(f"Expected string as source, got {type(source)}")

        if error_counts[source] >= MAX_ERRORS:
            raise Exception(f"Đã vượt quá số lần thử tối đa ({MAX_ERRORS}) cho nguồn ảnh này")

        try:
            if source.startswith(('http://', 'https://')):
                response = http_session.get(source, timeout=(5, 15))
                response.raise_for_status()
                image = Image.open(BytesIO(response.content)).convert('RGB')
            elif os.path.exists(source):
                image = Image.open(source).convert('RGB')
            else:
                raise FileNotFoundError(f"Không tìm thấy file hoặc URL không hợp lệ: {source}")

            if source in error_counts:
                del error_counts[source]

            return image

        except Exception as e:
            error_counts[source] += 1
            error_type = type(e).__name__

            if isinstance(e, requests.exceptions.RequestException):
                logger.error(f"Lỗi mạng khi tải ảnh từ {source}: {str(e)}")
            elif isinstance(e, FileNotFoundError):
                logger.error(f"Không tìm thấy file: {source}")
            else:
                logger.error(f"Lỗi không xác định ({error_type}) khi tải ảnh {source}: {str(e)}")

            if source not in self.failed_sources:
                self.failed_sources.append(source)

            raise

    def __getitem__(self, idx: int) -> Tuple[Optional[torch.Tensor], str]:
        image_source = self.image_sources[idx]

        try:
            image = self._load_image(image_source)
            if self.transform:
                image = self.transform(image)
            return image, image_source

        except Exception as e:
            logger.warning(f"Bỏ qua ảnh {image_source} do lỗi: {e}")
            return None, image_source

    def get_failed_sources(self) -> List[str]:
        return self.failed_sources
