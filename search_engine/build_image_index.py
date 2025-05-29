import sqlite3
import os
import argparse
import numpy as np
import logging
from tqdm import tqdm # Thư viện tạo thanh tiến trình

import sys
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))  # Lùi lại 1 cấp để đến thư mục gốc
sys.path.insert(0, project_root)  # Thêm vào đầu sys.path để ưu tiên

from search_engine.faiss_indexer import FaissIndexer
from search_engine.feature_extractor import ImageFeatureExtractor
from config import Config

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_product_image_sources(db_path: str) -> list:
    """Truy vấn database để lấy danh sách (ID, Link_Image, Name_Product) từ bảng Product."""
    sources = []
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Lấy ID, Link_Image và Name_Product, bỏ qua những hàng có Link_Image là NULL hoặc trống
        cursor.execute("SELECT ID, Link_Image, Name_Product FROM Product WHERE Link_Image IS NOT NULL AND Link_Image != ''")
        rows = cursor.fetchall()
        conn.close()
        sources = [(row[0], row[1], row[2]) for row in rows] # Lưu ID, Link và Name
        logger.info(f"Tìm thấy {len(sources)} sản phẩm có Link_Image trong database.")
    except sqlite3.Error as e:
        logger.error(f"Lỗi khi truy vấn database {db_path}: {e}")
    except Exception as e:
        logger.error(f"Lỗi không xác định khi lấy nguồn ảnh: {e}")
    return sources

def main(config: Config):
    """Hàm chính để xây dựng chỉ mục ảnh."""
    logger.info("Bắt đầu quá trình xây dựng chỉ mục ảnh...")

    # 1. Lấy nguồn ảnh từ database
    image_sources_with_ids = get_product_image_sources(config.db_path)
    if not image_sources_with_ids:
        logger.warning("Không tìm thấy nguồn ảnh nào từ database. Kết thúc.")
        return

    # Tách ID, URL/Path và Name
    product_ids = [item[0] for item in image_sources_with_ids]
    image_sources = [item[1] for item in image_sources_with_ids]
    product_names = [item[2] for item in image_sources_with_ids]

    # 2. Khởi tạo Trình trích xuất Đặc trưng
    try:
        feature_extractor = ImageFeatureExtractor() # Tự động phát hiện device
        feature_dim = feature_extractor.feature_dim
    except Exception as e:
        logger.error(f"Không thể khởi tạo ImageFeatureExtractor: {e}")
        return

    # 3. Trích xuất đặc trưng theo batch
    try:
        # Sử dụng batch_size lớn hơn nếu có GPU mạnh
        batch_size = config.image_batch_size # Lấy từ config

        all_features_list, successful_sources = feature_extractor.extract_features_batch(image_sources, batch_size=batch_size)

        if not all_features_list:
            logger.warning("Không trích xuất được vector đặc trưng nào. Kết thúc.")
            return

        # Chuyển list các array thành một NumPy array lớn
        all_features_np = np.array(all_features_list).astype(np.float32)

        # Tạo metadata tương ứng với các vector đã trích xuất thành công
        # Tìm ID và tên sản phẩm cho các nguồn ảnh thành công
        source_to_info_map = {source: (pid, pname) for pid, source, pname in image_sources_with_ids}
        metadata_list = []
        valid_indices = [] # Lưu index của các vector hợp lệ trong mảng all_features_np
        for i, source in enumerate(successful_sources):
            product_info = source_to_info_map.get(source)
            if product_info is not None:
                product_id, product_name = product_info
                metadata_list.append({
                    'product_id': product_id, # Lưu ID sản phẩm
                    'product_name': product_name, # Lưu tên sản phẩm
                    'image_source': source
                })
                valid_indices.append(i)
            else:
                 logger.warning(f"Không tìm thấy product_id cho nguồn ảnh thành công: {source}")

        # Chỉ giữ lại các vector đặc trưng tương ứng với metadata hợp lệ
        if len(valid_indices) != all_features_np.shape[0]:
             logger.info(f"Lọc bỏ {all_features_np.shape[0] - len(valid_indices)} vector không có ID sản phẩm tương ứng.")
             all_features_np = all_features_np[valid_indices]

        if not metadata_list:
             logger.warning("Không có metadata hợp lệ nào được tạo. Kết thúc.")
             return

        logger.info(f"Trích xuất thành công {all_features_np.shape[0]} vector đặc trưng.")

    except Exception as e:
        logger.error(f"Lỗi trong quá trình trích xuất đặc trưng: {e}")
        # Cân nhắc giải phóng bộ nhớ nếu lỗi xảy ra ở đây
        if 'feature_extractor' in locals():
            del feature_extractor
        return
    finally:
         # Giải phóng bộ nhớ của model sau khi trích xuất xong
        if 'feature_extractor' in locals():
            del feature_extractor

    # 4. Khởi tạo và Xây dựng Chỉ mục FAISS
    try:
        # Lấy đường dẫn từ config
        index_path = config.image_index_path
        metadata_path = config.image_metadata_path

        # Tạo thư mục chứa nếu chưa có
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        os.makedirs(os.path.dirname(metadata_path), exist_ok=True)

        faiss_indexer = FaissIndexer(
            index_path=index_path,
            metadata_path=metadata_path,
            dimension=feature_dim
        )

        # Xây dựng chỉ mục mới (ghi đè nếu đã tồn tại)
        faiss_indexer.build_index(vectors=all_features_np, metadata=metadata_list)

        logger.info(f"Đã xây dựng và lưu chỉ mục FAISS tại: {index_path}")
        logger.info(f"Đã lưu metadata tại: {metadata_path}")

    except Exception as e:
        logger.error(f"Lỗi trong quá trình xây dựng hoặc lưu chỉ mục FAISS: {e}")

    logger.info("Hoàn tất quá trình xây dựng chỉ mục ảnh.")

if __name__ == "__main__":
    config = Config()
    main(config)
