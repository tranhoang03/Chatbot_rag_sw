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

    def _normalize_text_scores(self, text_results: List[Dict[str, Any]]) -> Dict[str, float]:
        """Chuẩn hóa điểm tìm kiếm văn bản thành xác suất"""
        if not text_results:
            return {}
            
        # Lấy điểm từ kết quả
        scores = {res['product_id']: res['score'] for res in text_results}
        
        # Chuyển đổi điểm thành xác suất bằng softmax
        values = np.array(list(scores.values()))
        exp_values = np.exp(values - np.max(values))  # Tránh overflow
        probs = exp_values / exp_values.sum()
        
        return {pid: float(prob) for pid, prob in zip(scores.keys(), probs)}

    def _normalize_image_scores(self, image_results: List[Tuple[Dict[str, Any], float]]) -> Dict[str, float]:
        """Chuẩn hóa khoảng cách ảnh thành xác suất"""
        if not image_results:
            return {}
            
        # Lấy khoảng cách từ kết quả
        distances = {meta['product_id']: dist for meta, dist in image_results}
        
        # Chuyển khoảng cách thành similarity
        # Sử dụng exponential decay để chuyển khoảng cách thành similarity
        max_dist = max(distances.values())
        similarities = {pid: np.exp(-dist/max_dist) for pid, dist in distances.items()}
        
        # Chuẩn hóa thành xác suất
        sum_sim = sum(similarities.values())
        probs = {pid: sim/sum_sim for pid, sim in similarities.items()}
        
        return probs

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
        print("\n=== Kết hợp kết quả theo Minimum Bayes Risk với xác suất chuẩn hóa ===")

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

        # Chuẩn hóa điểm thành xác suất
        print("\n=== Thông tin chuẩn hóa ===")
        text_probs = self._normalize_text_scores(text_results)
        image_probs = self._normalize_image_scores(image_results)
        print("Xác suất văn bản:", text_probs)
        print("Xác suất ảnh:", image_probs)

        # Tạo danh sách ứng viên
        candidates = {}
        for res in text_results:
            candidates[res['product_id']] = res
        for meta, _ in image_results:
            if meta['product_id'] not in candidates:
                candidates[meta['product_id']] = meta

        # Tính rủi ro kỳ vọng cho từng ứng viên
        risks = []
        for candidate_id in candidates:
            # Lấy xác suất từ hai phương pháp
            text_prob = text_probs.get(candidate_id, 0.0)
            image_prob = image_probs.get(candidate_id, 0.0)
            
            # Tính rủi ro kỳ vọng
            risk = alpha * (1 - image_prob) + (1 - alpha) * (1 - text_prob)
            risks.append((candidate_id, risk))

        print("\n=== Thông tin rủi ro ===")
        for candidate_id, risk in risks:
            print(f"Candidate {candidate_id}:")
            print(f"  Text prob: {text_probs.get(candidate_id, 0.0):.4f}")
            print(f"  Image prob: {image_probs.get(candidate_id, 0.0):.4f}")
            print(f"  Total risk: {risk:.4f}")

        # Sắp xếp theo rủi ro thấp nhất
        risks.sort(key=lambda x: x[1])
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