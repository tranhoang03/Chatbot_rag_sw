import sqlite3
from typing import List, Dict, Any, Tuple
import numpy as np
from config import Config
from search_engine.feature_extractor import ImageFeatureExtractor
from search_engine.faiss_indexer import FaissIndexer
from system.embeddings import PhoBERTEmbeddings

class HybridSearchResult:
    def __init__(self, config: Config):
        self.config = config
        self.feature_extractor = ImageFeatureExtractor()
        self.indexer = FaissIndexer(
            index_path=config.image_index_path,
            metadata_path=config.image_metadata_path,
            dimension=self.feature_extractor.feature_dim
        )
        self.embeddings = PhoBERTEmbeddings()

    def _normalize_scores(self, results: List[Tuple[Any, float]]) -> Dict[str, float]:
        """Chuẩn hóa điểm và tính xác suất"""
        if not results:
            print("Không có kết quả để chuẩn hóa")
            return {}

        distances = {}
        for result in results:
            try:
                if isinstance(result, dict):
                    product_id = result.get('product_id')
                    if product_id:
                        distances[product_id] = result.get('score', 0.0)
                else:
                    meta, dist = result
                    product_id = meta.get('product_id') if isinstance(meta, dict) else meta.metadata.get('ID')
                    if product_id:
                        distances[product_id] = dist
            except Exception as e:
                print(f"Lỗi khi xử lý kết quả: {e}")

        values = np.array(list(distances.values()))
        mean, std = np.mean(values), np.std(values)
        normalized_dist = {pid: (dist - mean) / (std + 1e-6) for pid, dist in distances.items()}

        print("\n=== Điểm sau chuẩn hóa (z-score) ===")
        for pid, dist in normalized_dist.items():
            print(f"Product {pid}: Normalized distance = {dist:.4f}")

        similarities = {pid: np.exp(-dist) for pid, dist in normalized_dist.items()}

        print("\n=== Similarity scores ===")
        for pid, sim in similarities.items():
            print(f"Product {pid}: Similarity = {sim:.4f}")

        sum_sim = sum(similarities.values())
        probs = {pid: sim / sum_sim for pid, sim in similarities.items()}

        print("\n=== Xác suất cuối cùng ===")
        for pid, prob in probs.items():
            print(f"Product {pid}: Probability = {prob:.4f}")

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
            return self.indexer.search(query_feature, k)
        except Exception as e:
            print(f"Lỗi khi tìm kiếm theo đặc trưng ảnh: {e}")
            return []

    def combine_results_mbr(self,
                            text_results: list,
                            image_results: list,
                            alpha: float = 0.5,
                            k: int = 3) -> list:
        print("\n=== Kết hợp kết quả theo Minimum Bayes Risk với tổng độ tương đồng mô tả sản phẩm ===")

        text_probs = self._normalize_scores([
            (r, r.get('score', 0.0)) if isinstance(r, dict) else r for r in text_results
        ])
        image_probs = self._normalize_scores(image_results)

        candidates = {}
        for results in (text_results, image_results):
            for result in results:
                meta = result if isinstance(result, dict) else result[0]
                product_id = meta.get('product_id') if isinstance(meta, dict) else meta.metadata.get('ID')
                if product_id and product_id not in candidates:
                    candidates[product_id] = meta if isinstance(meta, dict) else meta.metadata

        def compute_similarity(desc1, desc2):
            emb1 = np.array(self.embeddings.embed_query(desc1))
            emb2 = np.array(self.embeddings.embed_query(desc2))
            return float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2) + 1e-8))

        scores = []
        for candidate_id, candidate in candidates.items():
            desc_cand = candidate.get('description', '')
            sim_image = sum(
                image_probs.get(meta.get('product_id'), 0.0) * compute_similarity(desc_cand, meta.get('description', ''))
                for meta, _ in image_results
            )
            sim_text = sum(
                text_probs.get(
                    (r if isinstance(r, dict) else r[0]).get('product_id'), 0.0
                ) * compute_similarity(desc_cand, (r if isinstance(r, dict) else r[0]).get('description', ''))
                for r in text_results
            )
            scores.append((candidate_id, alpha * sim_image + (1 - alpha) * sim_text))

        scores.sort(key=lambda x: -x[1])
        top_candidates = [candidates[cid] for cid, _ in scores[:k]]

        print("\n=== Top kết quả sau khi áp dụng MBR ===")
        for i, item in enumerate(top_candidates):
            print(f"Rank {i+1}: ID {item.get('ID', item.get('product_id'))}, Mô tả: {item.get('description', '')}")

        return top_candidates

    def _get_product_info(self, product_id: int) -> Dict[str, Any]:
        """Lấy thông tin sản phẩm từ database với giá các biến thể sử dụng GROUP_CONCAT"""
        try:
            conn = sqlite3.connect(self.config.db_path)
            cursor = conn.cursor()

            # Sử dụng GROUP_CONCAT để gộp thông tin biến thể thành một chuỗi
            cursor.execute("""
                SELECT
                    p.Name_Product as name,
                    p.Descriptions as description,
                    v.Price as price,
                    'Biến thể: ' || GROUP_CONCAT(v."Beverage Option", ', ') || '; Giá: ' || GROUP_CONCAT(v.Price || ' VND', ', ') as variant_prices
                FROM Product p
                JOIN Variant v ON p.ID = v.Product_id
                WHERE p.ID = ?
                GROUP BY p.ID, p.Name_Product, p.Descriptions
            """, (product_id,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    'name': row[0],
                    'description': row[1],
                    'price': row[2],
                    'variant_prices': row[3] if row[3] else 'Không có thông tin giá'
                }
            return None
        except Exception as e:
            print(f"Lỗi khi lấy thông tin sản phẩm {product_id}: {e}")
            return None
