import faiss
import numpy as np
import pickle
import os
import logging
from typing import List, Tuple, Dict, Any, Optional

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FaissIndexer:
    """Quản lý việc xây dựng, lưu trữ và tìm kiếm chỉ mục FAISS cho vector đặc trưng ảnh."""

    def __init__(self, index_path: str, metadata_path: str, dimension: int):
        """
        Khởi tạo FaissIndexer.

        Args:
            index_path (str): Đường dẫn để lưu/tải file chỉ mục FAISS (.index).
            metadata_path (str): Đường dẫn để lưu/tải file metadata (.pkl).
            dimension (int): Số chiều của vector đặc trưng (ví dụ: 768 cho ViT-B/16).
        """
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.dimension = dimension
        self.index: Optional[faiss.Index] = None
        self.metadata: List[Dict[str, Any]] = []  # Metadata sẽ là list các dict

        # Tải chỉ mục và metadata nếu tồn tại
        self.load_index()

    def build_index(self, vectors: np.ndarray, metadata: List[Dict[str, Any]]):
  
        if vectors.shape[0] != len(metadata):
            raise ValueError(f"Số lượng vector ({vectors.shape[0]}) không khớp với số lượng metadata ({len(metadata)}).")
        if vectors.shape[1] != self.dimension:
            raise ValueError(f"Chiều của vector ({vectors.shape[1]}) không khớp với chiều đã khai báo ({self.dimension}).")

        logger.info(f"Bắt đầu xây dựng chỉ mục FAISS mới với {vectors.shape[0]} vector...")

        # Sử dụng IndexFlatL2 vì chúng ta đã chuẩn hóa L2 các vector
        self.index = faiss.IndexFlatL2(self.dimension)

        if vectors.dtype != np.float32:
            logger.warning(f"Chuyển đổi kiểu dữ liệu vector từ {vectors.dtype} sang float32.")
            vectors = vectors.astype(np.float32)

        self.index.add(vectors)
        self.metadata = metadata

        logger.info(f"Xây dựng chỉ mục hoàn tất. Tổng số vector trong chỉ mục: {self.index.ntotal}")
        self.save_index()

    def add_items(self, vectors: np.ndarray, metadata: List[Dict[str, Any]]):
      
        if self.index is None:
            logger.warning("Chỉ mục chưa được khởi tạo. Gọi build_index trước.")
            self.build_index(vectors, metadata)
            return

        if vectors.shape[0] != len(metadata):
            raise ValueError("Số lượng vector không khớp với số lượng metadata.")
        if vectors.shape[1] != self.dimension:
            raise ValueError(f"Chiều của vector ({vectors.shape[1]}) không khớp với chiều của chỉ mục ({self.dimension}).")

        if vectors.dtype != np.float32:
            vectors = vectors.astype(np.float32)

        logger.info(f"Thêm {vectors.shape[0]} vector mới vào chỉ mục...")
        self.index.add(vectors)
        self.metadata.extend(metadata)
        logger.info(f"Thêm hoàn tất. Tổng số vector trong chỉ mục: {self.index.ntotal}")

        self.save_index()

    def search(self, query_vector: np.ndarray, k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
      
        if self.index is None or self.index.ntotal == 0:
            logger.warning("Chỉ mục trống hoặc chưa được tải.")
            return []

        if query_vector.ndim == 1:
            query_vector = np.expand_dims(query_vector, axis=0)  # Chuyển thành batch size 1

        if query_vector.shape[1] != self.dimension:
            raise ValueError(f"Chiều của vector truy vấn ({query_vector.shape[1]}) không khớp với chiều của chỉ mục ({self.dimension}).")

        if query_vector.dtype != np.float32:
            query_vector = query_vector.astype(np.float32)

        actual_k = min(k, self.index.ntotal)
        if actual_k == 0:
            return []

        logger.debug(f"Tìm kiếm {actual_k} hàng xóm gần nhất...")
        distances, indices = self.index.search(query_vector, actual_k)

        results = []
        for i, dist in zip(indices[0], distances[0]):
            if i != -1:  # faiss trả về -1 nếu không đủ k kết quả
                try:
                    meta = self.metadata[i]
                    results.append((meta, float(dist)))
                except IndexError:
                    logger.error(f"Lỗi truy cập metadata tại index {i} trong khi index size là {len(self.metadata)}")
                except Exception as e:
                    logger.error(f"Lỗi không xác định khi xử lý kết quả tại index {i}: {e}")

        logger.debug(f"Tìm thấy {len(results)} kết quả.")
        return results

    def save_index(self):
        """Lưu chỉ mục FAISS và metadata vào file."""
        if self.index is None:
            logger.warning("Không có chỉ mục để lưu.")
            return

        try:
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
            os.makedirs(os.path.dirname(self.metadata_path), exist_ok=True)

            logger.info(f"Lưu chỉ mục FAISS vào: {self.index_path}")
            faiss.write_index(self.index, self.index_path)

            logger.info(f"Lưu metadata vào: {self.metadata_path}")
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(self.metadata, f)
            logger.info("Lưu chỉ mục và metadata thành công.")

        except Exception as e:
            logger.error(f"Lỗi khi lưu chỉ mục hoặc metadata: {e}")
            raise

    def load_index(self):
        """Tải chỉ mục FAISS và metadata từ file nếu tồn tại."""
        loaded = False
        if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
            try:
                logger.info(f"Đang tải chỉ mục FAISS từ: {self.index_path}")
                self.index = faiss.read_index(self.index_path)
                logger.info(f"Tải chỉ mục thành công. Số vector: {self.index.ntotal}, Chiều: {self.index.d}")

                if self.index.d != self.dimension:
                    logger.warning(f"Chiều của chỉ mục đã tải ({self.index.d}) không khớp với chiều khai báo ({self.dimension}). Sẽ sử dụng chiều từ file.")
                    self.dimension = self.index.d

                logger.info(f"Đang tải metadata từ: {self.metadata_path}")
                with open(self.metadata_path, 'rb') as f:
                    self.metadata = pickle.load(f)
                logger.info(f"Tải metadata thành công. Số lượng metadata: {len(self.metadata)}")

                if self.index.ntotal != len(self.metadata):
                    logger.error(f"Số lượng vector trong chỉ mục ({self.index.ntotal}) không khớp với metadata ({len(self.metadata)}). Chỉ mục có thể bị hỏng.")
                else:
                    loaded = True

            except faiss.FaissException as e:
                logger.error(f"Lỗi FAISS khi tải chỉ mục từ {self.index_path}: {e}")
                self.index = None
                self.metadata = []
            except FileNotFoundError:
                logger.warning("Không tìm thấy file chỉ mục hoặc metadata. Sẽ tạo mới khi cần.")
                self.index = None
                self.metadata = []
            except pickle.UnpicklingError as e:
                logger.error(f"Lỗi khi giải nén metadata từ {self.metadata_path}: {e}")
                self.index = None
                self.metadata = []
            except Exception as e:
                logger.error(f"Lỗi không xác định khi tải chỉ mục hoặc metadata: {e}")
                self.index = None
                self.metadata = []
        else:
            logger.info("Không tìm thấy file chỉ mục hoặc metadata. Chỉ mục sẽ được tạo khi có dữ liệu.")

        if not loaded and self.index is None:
            logger.info(f"Khởi tạo chỉ mục FAISS trống với chiều {self.dimension}")
            self.index = faiss.IndexFlatL2(self.dimension)
            self.metadata = []

    def get_index_size(self) -> int:
        """Trả về số lượng vector hiện có trong chỉ mục."""
        return self.index.ntotal if self.index else 0
