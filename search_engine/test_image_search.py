import os
os.environ['KMP_DUPLICATE_LIB_OK']='TRUE'
import requests
import numpy as np
from io import BytesIO
from search_engine.feature_extractor import ImageFeatureExtractor
from search_engine.faiss_indexer import FaissIndexer
import logging
from typing import List, Tuple
import matplotlib.pyplot as plt
from PIL import Image
from config import Config

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageSearchTester:
    def __init__(self, image_dir: str, config: Config = None):
        self.image_dir = image_dir
        self.config = config or Config()
        
        # Khởi tạo feature extractor
        self.feature_extractor = ImageFeatureExtractor()
        
        # Load sẵn FAISS index đã được xây dựng trước đó
        self.indexer = FaissIndexer(
            index_path=self.config.image_index_path,
            metadata_path=self.config.image_metadata_path,
            dimension=self.feature_extractor.feature_dim
        )
    
    def _load_image(self, image_input: str) -> Image.Image:
        """Tải ảnh từ URL hoặc file local."""
        try:
            if image_input.lower().startswith(('http://', 'https://')):
                response = requests.get(image_input)
                response.raise_for_status()  # Raise an error for bad HTTP status codes
                img = Image.open(BytesIO(response.content)).convert("RGB")
            else:
                if not os.path.exists(image_input):
                    logger.error(f"Không tìm thấy tệp ảnh: {image_input}")
                    return None
                img = Image.open(image_input).convert("RGB")
            return img
        except requests.exceptions.RequestException as e:
            logger.error(f"Lỗi khi tải ảnh từ URL {image_input}: {e}")
        except Exception as e:
            logger.error(f"Lỗi khi mở ảnh {image_input}: {e}")
        return None

    def test_search(self, query_image_path: str, k: int = 5) -> List[Tuple[str, float]]:
        """Thực hiện tìm kiếm ảnh tương tự trong index."""
        query_img = self._load_image(query_image_path)
        if query_img is None:
            logger.error(f"Không thể tải ảnh truy vấn từ {query_image_path}")
            return []
        
        # Thay đổi để truyền đường dẫn tệp thay vì đối tượng Image
        query_feature = self.feature_extractor.extract_features(query_image_path)
        if query_feature is None:
            logger.error(f"Không thể trích xuất đặc trưng từ ảnh {query_image_path}")
            return []
        
        # Tìm kiếm trong FAISS index
        results = self.indexer.search(query_feature, k)
        if not results:
            logger.warning(f"Không có kết quả tìm kiếm cho ảnh {query_image_path}")
            return []
        
        # Trả về kết quả tìm kiếm
        return [(meta['image_source'], 1 - (dist / 2)) for meta, dist in results]

    def visualize_results(self, query_image_path: str, results: List[Tuple[str, float]], save_path: str = None):
        """Hiển thị ảnh truy vấn và các ảnh tương tự, kèm đường dẫn + similarity score."""
        if not results:
            logger.error("Không có kết quả để hiển thị.")
            return
        
        n_results = len(results)
        plt.figure(figsize=(4 * (n_results + 1), 5))

        # Hiển thị ảnh truy vấn
        plt.subplot(1, n_results + 1, 1)
        query_img = self._load_image(query_image_path)
        if query_img:
            plt.imshow(query_img)
            plt.title("Query\n(Ảnh truy vấn)")
        plt.axis('off')

        # Hiển thị các kết quả
        for i, (result_path, similarity) in enumerate(results, 2):
            result_img = self._load_image(result_path)
            if result_img:
                plt.subplot(1, n_results + 1, i)
                plt.imshow(result_img)
                title = f"Score: {similarity:.2f}\n{os.path.basename(result_path)}"
                plt.title(title, fontsize=10)
                plt.axis('off')

        if save_path:
            plt.savefig(save_path, bbox_inches='tight')
        plt.tight_layout()
        plt.show()

# Ví dụ chạy thử
if __name__ == "__main__":
    config = Config()
    tester = ImageSearchTester(image_dir="test_images", config=config)
    
    # Có thể dùng URL hoặc file local
    query_img = "test_images/example.jpg"
    
    results = tester.test_search(query_img)
    tester.visualize_results(query_img, results)
