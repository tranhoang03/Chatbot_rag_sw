# Hệ Thống Trợ Lý Cửa Hàng Đồ Uống Thông Minh

Hệ thống trợ lý AI thông minh cho cửa hàng đồ uống, tích hợp nhiều tính năng để nâng cao trải nghiệm khách hàng.

## 🌟 Tính Năng Chính

### 1. Xác Thực Khuôn Mặt
- Đăng nhập thông qua nhận diện khuôn mặt
- Tích hợp webcam realtime để xác thực nhanh chóng
- Hỗ trợ đăng ký khuôn mặt mới cho khách hàng

### 2. Chatbot AI Thông Minh
- Tương tác tự nhiên bằng tiếng Việt
- Đề xuất đồ uống dựa trên sở thích và lịch sử
- Hỗ trợ truy vấn thông tin sản phẩm
- Tìm kiếm ngữ nghĩa trong lịch sử mua hàng
- Tích hợp với Gemini AI cho phản hồi chính xác

### 3. Tìm kiếm sản phẩm tương tự bằng hình ảnh
- Phân tích và nhận diện đồ uống từ ảnh
- Đề xuất sản phẩm tương tự dựa trên hình ảnh
- Tìm kiếm sản phẩm bằng hình ảnh

<<<<<<< Updated upstream
=======
### 4. Voice Chat
- Chuyển đổi văn bản thành giọng nói với ElevenLabs API
- Hỗ trợ nhiều giọng đọc khác nhau
- Điều chỉnh tốc độ đọc

>>>>>>> Stashed changes
## 🛠 Công Nghệ Sử Dụng

### Backend
- **Flask**: Framework web chính
- **Flask-SocketIO**: Xử lý kết nối realtime
- **SQLite**: Database lưu trữ dữ liệu
- **FAISS**: Tìm kiếm vector hiệu quả

### AI/ML
- **InsightFace** (tùy chọn): Nhận diện khuôn mặt
- **PhoBERT**: Xử lý ngôn ngữ tiếng Việt
- **Google Generative AI**: Chatbot thông minh
- **OpenCV & Pillow**: Xử lý hình ảnh
- **TorchVision**: Xử lý và phân tích hình ảnh

### Frontend
- **HTML5/CSS3**: Giao diện người dùng
- **JavaScript**: Tương tác client-side
- **WebSocket**: Kết nối realtime

## 📦 Cài Đặt

### Yêu Cầu Hệ Thống
- Python 3.8+
- Webcam cho tính năng nhận diện khuôn mặt
- RAM tối thiểu 4GB
- Ổ cứng trống 1GB

### Bước 1: Clone Repository
```bash
git clone https://github.com/tranhoang03/Chatbot_rag_sw.git
cd Chatbot_rag_sw
```

### Bước 2: Thiết Lập Môi Trường
```bash
# Tạo môi trường ảo
python -m venv venv

# Kích hoạt môi trường
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Cài đặt dependencies
pip install -r requirements.txt
```

#### Lưu ý về các thư viện đặc biệt

1. **InsightFace**

   Thư viện InsightFace yêu cầu Microsoft Visual C++ Build Tools để cài đặt. Nếu bạn gặp lỗi khi cài đặt InsightFace, bạn cần:

   - Cài đặt [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
   - Sau đó cài đặt InsightFace:
     ```bash
     pip install insightface
     ```

   InsightFace là thư viện cần thiết cho tính năng xác thực khuôn mặt của ứng dụng.

2. **PyAV (av)**

   Thư viện PyAV (av) yêu cầu FFmpeg để hoạt động. Nếu bạn gặp lỗi khi cài đặt hoặc sử dụng PyAV, bạn cần:

   - Windows: Tải và cài đặt [FFmpeg](https://ffmpeg.org/download.html)
   - Linux: `sudo apt-get install ffmpeg`
   - macOS: `brew install ffmpeg`

   PyAV được sử dụng cho xử lý âm thanh trong tính năng voice chat.

### Bước 3: Cấu Hình
1. Tạo file `.env` với nội dung:
```env
# Server
HOST=0.0.0.0
PORT=5000

# Database
DB_PATH=Database.db
DB_TIMEOUT=30

# Vector Store
VECTOR_STORE_PATH=search_engine/vector_store
DESCRIPTION_VECTOR_STORE_PATH=search_engine/description_store
TOP_K_RESULTS=3

# AI Models
EMBEDDING_MODEL=vinai/phobert-base
LLM_MODEL=gemini-1.5-flash-latest
LLM_TEMPERATURE=0

# Image Processing
IMAGE_BATCH_SIZE=32
IMAGE_FAISS_INDEX_PATH=search_engine/image_index/index.faiss
IMAGE_FAISS_METADATA_PATH=search_engine/image_index/metadata.pkl

# Chat
MAX_HISTORY_PER_USER=3

# API Keys
GOOGLE_API_KEY=your_google_api_key
HUGGINGFACE_HUB_TOKEN=your_huggingface_token
ELEVENLABS_API_KEY=your_elevenlabs_api_key

# Security
FLASK_SECRET_KEY=your_flask_secret_key
```

### Bước 4: Khởi Tạo Database
```bash
# Database sẽ tự tạo khi chạy lần đầu
# Nếu cần dữ liệu mẫu, import vào Database.db
```

### Bước 5: Xây Dựng Chỉ Mục Hình Ảnh Sản Phẩm
```bash
python search_engine/build_image_index.py
```

### Bước 6: Khởi Chạy
```bash
python app.py
```

## 📁 Cấu Trúc Dự Án

```
├── app.py                # Flask app chính, định nghĩa endpoint và socket
├── config.py             # Cấu hình hệ thống, biến môi trường
├── utils.py              # Hàm tiện ích
├── system/               # Các module lõi
│   ├── face_auth.py      # Xác thực khuôn mặt (yêu cầu InsightFace)
│   ├── face_auth_mock.py # Phiên bản mock của xác thực khuôn mặt (không yêu cầu InsightFace)
│   └── rag_system.py     # Hệ thống RAG (Retrieval-Augmented Generation)
├── search_engine/        # Các file phục vụ tìm kiếm, Vector Store FAISS, trích xuất đặc trưng ảnh,..
├── models/               # Mô hình phục vụ xác minh khuôn mặt(ONNX, PhoBERT, ...)
├── templates/            # HTML templates (auth, chat, register, ...)
├── static/               # CSS, JS
├── cus_img/              # Ảnh khách hàng
├── Database.db           # SQLite database
├── requirements.txt      # Thư viện Python
└── README.md
```

## 🔌 API Endpoints

### Xác Thực & Người Dùng
- `GET /`: Trang chủ - Hiển thị trang chat nếu đã đăng nhập, trang xác thực nếu chưa
- `GET /authenticate`: Trang xác thực khuôn mặt
- `POST /confirm_auth`: Xác nhận xác thực khuôn mặt thành công
- `GET /register`: Trang đăng ký người dùng mới
- `POST /register`: Xử lý đăng ký người dùng mới với thông tin và ảnh khuôn mặt
- `GET /logout`: Đăng xuất và xóa session
- `GET /start_anonymous_chat`: Bắt đầu phiên chat ẩn danh

### Chat & Tương Tác
- `POST /chat`: Xử lý tin nhắn chat từ người dùng đã xác thực hoặc ẩn danh
  - Input: JSON với trường `prompt`
  - Output: JSON với `role`, `content`, và `product_images`

### Xử Lý Hình Ảnh
- `POST /process_image`: Phân tích hình ảnh đồ uống
  - Input: Form data với file hình ảnh
  - Output: JSON với `content` và `product_images`



## 🔒 Bảo Mật

### Xác Thực
- Mã hóa embedding khuôn mặt
- Giới hạn thời gian xác thực 5 giây

## ⚠️ Xử Lý Sự Cố

### Lỗi "No module named 'insightface'"
Nếu bạn gặp lỗi này, bạn cần cài đặt InsightFace như hướng dẫn ở phần "Lưu ý về các thư viện đặc biệt". Đảm bảo bạn đã cài đặt Microsoft Visual C++ Build Tools trước khi cài đặt InsightFace.

### Lỗi "No module named 'av'"
Nếu bạn gặp lỗi này, bạn cần cài đặt PyAV và FFmpeg như hướng dẫn ở phần "Lưu ý về các thư viện đặc biệt". Đảm bảo bạn đã cài đặt FFmpeg trước khi cài đặt PyAV.

```bash
pip install av
```

### Lỗi "No module named 'torchvision'"
Cài đặt thư viện torchvision:
```bash
pip install torchvision
```

### Lỗi khi tải mô hình
Đảm bảo bạn đã cung cấp API key hợp lệ trong file .env và có kết nối internet ổn định.

### Lỗi liên quan đến InsightFace
Nếu bạn gặp lỗi liên quan đến InsightFace khi chạy ứng dụng, hãy kiểm tra:
1. Đã cài đặt đúng phiên bản InsightFace (0.5.0 hoặc cao hơn)
2. Đã cài đặt đầy đủ các thư viện phụ thuộc của InsightFace
3. Đã cài đặt Microsoft Visual C++ Build Tools

Bạn có thể thử cài đặt lại InsightFace với lệnh:
```bash
pip uninstall insightface
pip install insightface
```

### Lỗi liên quan đến FFmpeg
Nếu bạn gặp lỗi liên quan đến FFmpeg khi sử dụng tính năng voice chat, hãy kiểm tra:
1. Đã cài đặt FFmpeg và thêm vào PATH
2. Đã cài đặt PyAV (av) đúng cách

Bạn có thể thử cài đặt lại PyAV với lệnh:
```bash
pip uninstall av
pip install av
```


## 🤝 Đóng Góp

Mọi ý kiến, đóng góp xin gửi về:
- tranhoang0320@gmail.com
- trth.thanhue@gmail.com



## Tham khảo

- InsightFace cho công nghệ nhận diện khuôn mặt
- Google Generative AI cho chatbot
- VinAI cho PhoBERT
- Meta cho FAISS
- ElevenLabs cho công nghệ chuyển văn bản thành giọng nói
- PyAV và FFmpeg cho xử lý âm thanh
