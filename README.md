# Hệ Thống Trợ Lý Cửa Hàng Đồ Uống Thông Minh

Hệ thống trợ lý thông minh cho cửa hàng đồ uống, tích hợp xác thực khuôn mặt, RAG (Retrieval-Augmented Generation) và nhận dạng hình ảnh để cung cấp dịch vụ khách hàng cá nhân hóa.

## 🚀 Tính Năng Chính

### 1. Xác Thực Khuôn Mặt
- Nhận dạng khuôn mặt thời gian thực
- Xác thực khách hàng an toàn
- Quản lý phiên đăng nhập
- Hỗ trợ chat ẩn danh

### 2. Hệ Thống Chat Thông Minh
- Phản hồi theo ngữ cảnh sử dụng RAG
- Đề xuất cá nhân hóa dựa trên lịch sử mua hàng
- Hỗ trợ tìm kiếm SQL và tìm kiếm ngữ nghĩa
- Xử lý hội thoại đa lượt

### 3. Nhận Dạng Hình Ảnh
- Nhận dạng và phân tích đồ uống từ hình ảnh
- Phát hiện thành phần và cấu tạo
- Đề xuất đồ uống thông minh dựa trên độ tương đồng hình ảnh
- Tích hợp OCR để trích xuất văn bản từ hình ảnh

### 4. Tích Hợp Cơ Sở Dữ Liệu
- SQLite để lưu trữ thông tin sản phẩm và khách hàng
- Vector store cho khả năng tìm kiếm ngữ nghĩa
- Theo dõi lịch sử mua hàng
- Quản lý sở thích khách hàng

## 🛠 Kiến Trúc Kỹ Thuật

### Thành Phần Chính
- **Xác thực khuôn mặt**: Sử dụng InsightFace cho phát hiện và nhận dạng khuôn mặt
- **Hệ thống RAG**: Kết hợp PhoBERT embeddings với Google Generative AI
- **Vector Store**: FAISS cho tìm kiếm tương đồng hiệu quả
- **Giao diện Web**: Flask + SocketIO cho giao tiếp thời gian thực

### Công Nghệ Chính
- Flask cho máy chủ web
- Socket.IO cho giao tiếp thời gian thực
- Google Generative AI cho xử lý ngôn ngữ tự nhiên
- FAISS cho tìm kiếm tương đồng vector
- PhoBERT cho hiểu ngôn ngữ tiếng Việt
- SQLite cho lưu trữ dữ liệu

## 📦 Cài Đặt và Chạy

1. Clone repository:
   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

2. Tạo và kích hoạt môi trường ảo:
   ```bash
   python -m venv venv
   # Trên Windows:
   venv\Scripts\activate
   # Trên Unix/MacOS:
   source venv/bin/activate
   ```

3. Cài đặt các thư viện cần thiết:
   ```bash
   pip install -r requirements.txt
   ```

4. Cấu hình biến môi trường trong file `.env`:
   ```
   GOOGLE_API_KEY=your_google_api_key
   HUGGINGFACE_HUB_TOKEN=your_huggingface_token
   ```

5. Khởi tạo cơ sở dữ liệu và vector store:
   ```bash
   python init_db.py
   ```

6. Chạy ứng dụng:
   ```bash
   python app.py
   ```

## 📁 Cấu Trúc Dự Án

```
project/
├── app.py                 # Ứng dụng Flask chính
├── config.py             # Cấu hình hệ thống
├── utils.py             # Các hàm tiện ích
├── system/              # Hệ thống chính
│   ├── face_auth.py     # Hệ thống xác thực khuôn mặt
│   ├── rag_system.py    # Triển khai RAG
│   ├── extract_info.py  # Phân tích hình ảnh
│   └── prompts.py       # Các prompt hệ thống
├── search_engine/       # Công cụ tìm kiếm
│   ├── hybrid_search.py # Tìm kiếm lai
│   ├── faiss_indexer.py # FAISS indexer
│   └── feature_extractor.py # Trích xuất đặc trưng
├── templates/           # Templates HTML
├── vector_store/        # FAISS vector stores
├── Database.db         # Cơ sở dữ liệu SQLite
└── requirements.txt    # Các thư viện cần thiết
```

## 🔌 API Endpoints

- `/`: Giao diện chính
- `/authenticate`: Xác thực khuôn mặt
- `/chat`: Xử lý tin nhắn chat
- `/process_image`: Phân tích hình ảnh
- `/confirm_auth`: Xác nhận xác thực
- `/register`: Đăng ký người dùng mới

## 🔒 Bảo Mật

- API keys được lưu trữ an toàn trong biến môi trường
- Face embeddings được lưu trữ bảo mật trong database
- Ngăn chặn SQL injection thông qua kiểm tra truy vấn
- Quản lý phiên an toàn
- Giới hạn số lần thử xác thực

## 🤝 Đóng Góp

Mọi đóng góp và đề xuất cải tiến đều được hoan nghênh!

## 📄 Giấy Phép

[Thêm thông tin giấy phép tại đây]

## Tham khảo

- InsightFace cho nhận dạng khuôn mặt
- Google cho khả năng Generative AI
- VinAI cho mô hình PhoBERT
- Meta AI cho FAISS 
