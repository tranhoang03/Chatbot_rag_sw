# Hệ Thống Trợ Lý Cửa Hàng Đồ Uống Thông Minh

Hệ thống trợ lý AI cho cửa hàng đồ uống, tích hợp xác thực khuôn mặt, RAG (Retrieval-Augmented Generation), nhận dạng hình ảnh và chat thông minh, giúp cá nhân hóa trải nghiệm khách hàng.

## 🚀 Tính Năng Nổi Bật

- **Xác thực khuôn mặt**: Đăng nhập, nhận diện khách hàng qua webcam, bảo mật và tiện lợi.
- **Chat AI thông minh**: Trả lời tự động, đề xuất đồ uống, hỗ trợ truy vấn SQL, tìm kiếm ngữ nghĩa dựa trên lịch sử mua hàng.
- **Nhận dạng hình ảnh**: Phân tích, nhận diện đồ uống từ ảnh, trích xuất thành phần, đề xuất sản phẩm tương tự.
- **Quản lý khách hàng & sản phẩm**: Lưu trữ thông tin, lịch sử mua hàng, sở thích, hỗ trợ cá nhân hóa.
- **Giao diện web hiện đại**: Đăng nhập, chat, đăng ký, xác thực, thao tác trực quan.

## 🛠 Công Nghệ Sử Dụng

- **Flask** & **Flask-SocketIO**: Xây dựng web, realtime chat.
- **InsightFace** & **ONNX**: Nhận diện khuôn mặt.
- **PhoBERT** & **Google Generative AI**: Xử lý ngôn ngữ tự nhiên tiếng Việt.
- **FAISS**: Tìm kiếm ngữ nghĩa, vector store.
- **OpenCV, Pillow**: Xử lý ảnh.
- **SQLite**: Lưu trữ dữ liệu.
- **dotenv**: Quản lý biến môi trường.

## 📦 Hướng Dẫn Cài Đặt

1. **Clone dự án:**
   ```bash
   git clone <repository-url>
   cd <repository-folder>
   ```

2. **Tạo và kích hoạt môi trường ảo:**
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Mac/Linux:
   source venv/bin/activate
   ```

3. **Cài đặt thư viện:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Tạo chỉ mục vector cho hình ảnh sản phẩm:**
   ```bash
   python search_engine/build_image_index.py
   ```
   Lệnh này sẽ tạo vector store cho hình ảnh sản phẩm từ database, sử dụng để tìm kiếm sản phẩm tương tự.

5. **Tạo file `.env` và điền các biến sau (tùy chỉnh nếu cần):**

   ```env
   # Cấu hình server
   HOST=0.0.0.0
   PORT=5000

   # Đường dẫn database
   DB_PATH=Database.db
   DB_TIMEOUT=30

   # Đường dẫn FAISS vector store
   VECTOR_STORE_PATH=search_engine/vector_store
   TOP_K_RESULTS=3

   # Đường dẫn FAISS cho mô tả sản phẩm
   DESCRIPTION_VECTOR_STORE_PATH=search_engine/description_store

   # Cấu hình model
   EMBEDDING_MODEL=vinai/phobert-base
   LLM_MODEL=gemini-1.5-flash-latest
   LLM_TEMPERATURE=0

   # Cấu hình tìm kiếm ảnh
   IMAGE_BATCH_SIZE=32
   IMAGE_FAISS_INDEX_PATH=search_engine/image_index/index.faiss
   IMAGE_FAISS_METADATA_PATH=search_engine/image_index/metadata.pkl

   # Lịch sử chat
   MAX_HISTORY_PER_USER=3

   # API keys
   GOOGLE_API_KEY=your_google_api_key
   HUGGINGFACE_HUB_TOKEN=your_huggingface_token

   # Flask secret key
   FLASK_SECRET_KEY=your_flask_secret_key
   ```

6. **Khởi tạo database (nếu chưa có):**
   - Database sẽ tự động tạo khi chạy lần đầu. Nếu cần, hãy import dữ liệu mẫu vào `Database.db`.

7. **Chạy ứng dụng:**
   ```bash
   python app.py
   ```

## 📁 Cấu Trúc Dự Án

```
├── app.py                # Flask app chính, định nghĩa endpoint và socket
├── config.py             # Cấu hình hệ thống, biến môi trường
├── utils.py              # Hàm tiện ích
├── system/               # Các module lõi: xác thực khuôn mặt, RAG, phân tích ảnh
├── search_engine/        # Tìm kiếm lai, FAISS, trích xuất đặc trưng ảnh
├── models/               # Mô hình AI (ONNX, PhoBERT, ...)
├── templates/            # HTML templates (auth, chat, register, ...)
├── static/               # CSS, JS, ảnh tĩnh
├── cus_img/              # Ảnh khuôn mặt khách hàng
├── Database.db           # SQLite database
├── requirements.txt      # Thư viện Python
└── README.md
```

## 🔌 Các API Endpoint

- `/` : Trang chính (chat, xác thực, đăng nhập)
- `/authenticate` : Xác thực khuôn mặt
- `/chat` : Xử lý chat AI
- `/process_image` : Phân tích ảnh đồ uống
- `/confirm_auth` : Xác nhận xác thực khuôn mặt
- `/register` : Đăng ký khách hàng mới
- `/logout` : Đăng xuất

## 🔒 Bảo Mật

- API key lưu trong biến môi trường, không commit lên git.
- Embedding khuôn mặt lưu trong database, bảo mật.
- Chống SQL injection, kiểm soát session.
- Giới hạn số lần xác thực, quản lý truy cập.

## 🤝 Đóng Góp

Mọi ý kiến, đóng góp xin gửi về:
- tranhoang0320@gmail.com
- trth.thanhue@gmail.com

## 📄 Giấy Phép

[Thêm thông tin giấy phép tại đây]

## Tham khảo

- InsightFace, Google Generative AI, VinAI PhoBERT, Meta FAISS
