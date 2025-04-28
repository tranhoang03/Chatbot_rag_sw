import sqlite3
from typing import List, Dict, Any, Tuple
from config import Config
from search_engine.feature_extractor import ImageFeatureExtractor
from search_engine.faiss_indexer import FaissIndexer
import numpy as np
from system.embeddings import PhoBERTEmbeddings

class HybridSearchResult:
    """Class để xử lý kết hợp kết quả từ hai phương pháp tìm kiếm"""
    def __init__(self, config: Config):
        self.config = config
        self.feature_extractor = ImageFeatureExtractor()
        self.indexer = FaissIndexer(
            index_path=config.image_index_path,
            metadata_path=config.image_metadata_path,
            dimension=self.feature_extractor.feature_dim
        )
        self.embeddings = PhoBERTEmbeddings()

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Tính cosine similarity giữa hai vector"""
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    def search_by_image_features(self, image_path: str, k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        """Tìm kiếm sản phẩm dựa trên đặc trưng ảnh"""
        try:
            print(f"\n=== Trích xuất đặc trưng ảnh từ {image_path} ===")
            query_feature = self.feature_extractor.extract_features(image_path)
            if query_feature is None:
                print("Không thể trích xuất đặc trưng ảnh")
                return []
            print("Trích xuất đặc trưng ảnh thành công")
            
            print("\n=== Tìm kiếm trong FAISS index ===")
            results = self.indexer.search(query_feature, k)
            return results
        except Exception as e:
            print(f"Lỗi khi tìm kiếm theo đặc trưng ảnh: {e}")
            return []

    def combine_results_mbr(self,
                            text_results: List[Dict[str, Any]],
                            image_results: List[Tuple[Dict[str, Any], float]],
                            alpha: float = 0.5,
                            k: int = 3) -> List[Dict[str, Any]]:
        print("\n=== Kết hợp kết quả theo Minimum Bayes Risk với Cosine Similarity ===")

        # Xử lý các trường hợp không có kết quả
        if not text_results and not image_results:
            print("Không có kết quả nào từ cả hai phương pháp tìm kiếm")
            return []
            
        if not text_results:
            print("Chỉ có kết quả từ tìm kiếm ảnh")
            return [meta for meta, _ in image_results[:k]]
            
        if not image_results:
            print("Chỉ có kết quả từ tìm kiếm văn bản")
            return text_results[:k]

        # Tiếp tục xử lý khi có kết quả từ cả hai phương pháp
        candidates = {}
        for res in text_results:
            candidates[res['product_id']] = res
        for meta, _ in image_results:
            if meta['product_id'] not in candidates:
                candidates[meta['product_id']] = meta

        # 2. Tạo vector embedding cho các mô tả
        descriptions = {meta['product_id']: meta['description'] for meta in candidates.values()}
        description_vectors = {}
        for pid, desc in descriptions.items():
            vector = self.embeddings.embed_query(desc)
            description_vectors[pid] = np.array(vector)

        # 3. Chuẩn hóa score FAISS
        def normalize_faiss(scores, is_distance=False):
            values = list(scores.values())
            if is_distance:
                max_val = max(values)
                min_val = min(values)
                return {k: 1.0 - ((v - min_val) / (max_val - min_val + 1e-6)) for k, v in scores.items()}
            else:
                max_val = max(values)
                min_val = min(values)
                return {k: (v - min_val) / (max_val - min_val + 1e-6) for k, v in scores.items()}

        text_scores = {res['product_id']: res['score'] for res in text_results}
        image_scores = {meta['product_id']: dist for meta, dist in image_results}

        text_scores = normalize_faiss(text_scores)
        image_scores = normalize_faiss(image_scores, is_distance=True)
        print("Score sau chuẩn hóa: ", text_scores, image_scores)

        # 4. Tính tổng rủi ro kỳ vọng cho từng ứng viên
        risks = []
        for candidate_id in candidates:
            vec_c = description_vectors[candidate_id]

            # Risk theo text
            risk_text = 0
            for tid, score in text_scores.items():
                sim = self._cosine_similarity(vec_c, description_vectors[tid])
                risk_text += score * (1 - sim)  # Chuyển similarity thành distance

            # Risk theo image
            risk_image = 0
            for iid, score in image_scores.items():
                sim = self._cosine_similarity(vec_c, description_vectors[iid])
                risk_image += score * (1 - sim)  # Chuyển similarity thành distance

            total_risk = alpha * risk_image + (1 - alpha) * risk_text
            risks.append((candidate_id, total_risk))

        print('Tổng rủi ro: ', risks)
        # 5. Chọn k ứng viên có rủi ro thấp nhất
        risks = sorted(risks, key=lambda x: x[1])
        top_candidates = [candidates[r[0]] for r in risks[:k]]

        print("\n=== Top kết quả sau khi áp dụng MBR ===")
        for i, item in enumerate(top_candidates):
            print(f"Rank {i+1}: ID {item['product_id']}, Mô tả: {item['description']}")

        return top_candidates

    def _get_product_info(self, product_id: int) -> Dict[str, Any]:
        """Lấy thông tin sản phẩm từ database"""
        try:
            conn = sqlite3.connect(self.config.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.Name_Product as name,
                       p.Descriptions as description,
                       v.Price as price
                FROM Product p
                JOIN Variant v ON p.ID = v.Product_id
                WHERE p.ID = ?
                LIMIT 1
            """, (product_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'name': row[0],
                    'description': row[1],
                    'price': row[2]
                }
            return None
        except Exception as e:
            print(f"Lỗi khi lấy thông tin sản phẩm {product_id}: {e}")
            return None 