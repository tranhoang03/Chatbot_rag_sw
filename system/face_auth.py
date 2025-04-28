import cv2
import numpy as np
import sqlite3
import json
import os
from pathlib import Path
from insightface.model_zoo import get_model
from insightface.model_zoo.arcface_onnx import ArcFaceONNX
from insightface.utils.face_align import norm_crop
from insightface.app.common import Face
BASE_DIR = Path(os.path.dirname(__file__)).parent  # Adjust this to your project structure

class DetectedFace:
    def __init__(self, bbox, landmarks=None, confidence=None):
        self.bbox = bbox
        self.landmarks = landmarks
        self.confidence = confidence

class ArcFaceRecognizer:
    def __init__(self):
        model_dir = os.path.join(BASE_DIR, 'models')
        recog_model_path = os.path.join(model_dir, 'w600k_r50.onnx')
        self._recognizer = ArcFaceONNX(recog_model_path)
        self._recognizer.prepare(ctx_id=0)  # Dùng GPU nếu có

    def _convert_input_face(self, face: DetectedFace) -> Face:
        # Chuyển landmarks thành dạng numpy array (5, 2) cho đúng định dạng input
        kps = np.array([ 
            face.landmarks["left_eye"], 
            face.landmarks["right_eye"], 
            face.landmarks["nose"], 
            face.landmarks["left_mouth"], 
            face.landmarks["right_mouth"]
        ], dtype=np.float32)

        # Đảm bảo kps có shape (5, 2)
        print(f"Keypoints: {kps}, Shape: {kps.shape}")
        
        return Face(
            bbox=np.array([ 
                face.bbox["x"], 
                face.bbox["y"], 
                face.bbox["x"] + face.bbox["w"], 
                face.bbox["y"] + face.bbox["h"]
            ]),
            kps=kps,
            det_score=face.confidence
        )

    def infer(self, image, face: DetectedFace) -> np.ndarray:
        converted_face = self._convert_input_face(face)
        aligned_face = norm_crop(image, converted_face.kps)
        features = self._recognizer.get_feat(aligned_face)
        return features


class FaceAuthTransformer:
    def __init__(self, model_name="det_10g.onnx"):
        """Initialize Face detection and recognition models."""
        print("🟢 Initializing FaceAuthTransformer...")

        model_dir = os.path.join(BASE_DIR, 'models')
        det_model_path = os.path.join(model_dir, model_name)

        if not os.path.exists(det_model_path):
            raise FileNotFoundError(f"Detection model not found at {det_model_path}")
        
        print(f"📦 Loading RetinaFace model from {det_model_path}")
        self.det_model = get_model(det_model_path)
        self.det_model.prepare(ctx_id=-1, input_size=(640, 640), det_thresh=0.5)
        print("✅ RetinaFace loaded successfully.")

        self.arcface_recognizer = ArcFaceRecognizer()
        print("✅ ArcFace Recognizer loaded successfully.")

    def recognize_face(self, frame):
        """Detect and recognize face in a single frame."""
        result = {'match': None, 'bbox': None, 'confidence': None, 'embedding': None}

        if frame is None:
            return result

        try:
            # Detect faces using RetinaFace
            bboxes, landmarks = self.det_model.detect(frame, max_num=0, metric='default')
            bboxes = sorted(bboxes, key=lambda b: b[4], reverse=True)
            x1, y1, x2, y2, conf = bboxes[0]
            if conf < self.det_model.det_thresh:
                return result  # No valid face detected

            # Extract the bounding box and landmarks
            x1, y1, x2, y2 = bboxes[0][:4].astype(int)
            result['bbox'] = [int(x1), int(y1), int(x2), int(y2)]
            result['confidence'] = float(conf)

            # Create a DetectedFace object with landmarks and bbox
            landmarks = landmarks[0]
            if landmarks.ndim == 2:
                landmarks = landmarks.flatten()

            try:
                face = DetectedFace(
                    bbox={"x": float(x1), "y": float(y1), "w": float(x2 - x1), "h": float(y2 - y1)},
                    landmarks={
                        "left_eye": (float(landmarks[0]), float(landmarks[1])),
                        "right_eye": (float(landmarks[2]), float(landmarks[3])),
                        "nose": (float(landmarks[4]), float(landmarks[5])),
                        "left_mouth": (float(landmarks[6]), float(landmarks[7])),
                        "right_mouth": (float(landmarks[8]), float(landmarks[9])),
                    },
                    confidence=float(conf)
                )

            except Exception as e:
                print(f"❌ Lỗi khi tạo landmark cho ảnh : {e}")
                return result

            # Crop face region for recognition
            image = frame

            # Extract features using ArcFace
            embedding = self.arcface_recognizer.infer(image, face)
            print(f"📸 Embedding từ frame: shape = {embedding.shape}")
            
            if embedding is not None and len(embedding.shape) == 2 and embedding.shape[0] == 1:
                embedding = embedding.squeeze(0)

            # Kiểm tra embedding hợp lệ
            if embedding is None or embedding.ndim != 1 or np.linalg.norm(embedding) == 0:
                print("❌ Embedding từ frame không hợp lệ.")
                result['match'] = False
                return result

            # Lưu embedding vào kết quả
            result['embedding'] = embedding

            # Compare with database
            match_info = find_matching_face(embedding)
            result['match'] = match_info if match_info else False

            return result

        except Exception as e:
            print(f"❌ Error during face recognition: {e}")
            return result

    def get_face_embedding(self, frame):
        """Get face embedding from a frame without matching with database."""
        result = self.recognize_face(frame)
        return result.get('embedding')



def find_matching_face(embedding, threshold=0.4):
    conn = None
    best_match_info = None
    max_similarity = -1.0

    db_path = os.path.join(BASE_DIR, 'Database.db')
    try:
        if not os.path.exists(db_path):
            print(f"❌ Database not found at {db_path}")
            return None

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT embedding, name, id FROM customers WHERE embedding IS NOT NULL")
        results = cursor.fetchall()

        if embedding is None or embedding.ndim != 1 or embedding.size == 0:
            print("❌ Embedding từ frame không hợp lệ.")
            return None

        for db_embedding_str, name, id in results:
            try:
                if not db_embedding_str:
                    continue

                db_embeddings = json.loads(db_embedding_str)
            
                for idx, emb in enumerate(db_embeddings):
                    db_embedding = np.array(emb, dtype=np.float32)


                    if db_embedding.ndim != 1 or db_embedding.size == 0:
                        print("⚠️ DB embedding bị lỗi hoặc rỗng.")
                        continue

                    if embedding.shape != db_embedding.shape:
                        print(f"⚠️ Không khớp chiều embedding: frame={embedding.shape}, db={db_embedding.shape} (name={name}, id={id})")
                        continue

                    similarity = np.dot(embedding, db_embedding) / (
                        np.linalg.norm(embedding) * np.linalg.norm(db_embedding)
                    )
                    similarity = float(similarity)

                    if similarity > max_similarity:
                        max_similarity = similarity
                        best_match_info = {'name': name, 'id': id, 'similarity': similarity}

            except json.JSONDecodeError:
                print("❌ Lỗi khi giải mã JSON embedding.")
                continue
            except Exception as e:
                print(f"❌ Lỗi khi xử lý embedding trong DB: {e}")
                continue

        if best_match_info and max_similarity >= threshold:
            print(f"🎯 Match found: {best_match_info['name']} (ID: {best_match_info['id']}), Similarity: {max_similarity:.4f}")
            return {'name': best_match_info['name'], 'id': best_match_info['id']}

        print("🔍 Không tìm thấy match nào đạt ngưỡng.")
        return None

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
    finally:
        if conn:
            conn.close()
