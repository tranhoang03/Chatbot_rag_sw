import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import eventlet
eventlet.monkey_patch()
import base64
import os
from flask import Flask, render_template, request, session, jsonify, redirect, url_for, Response
from flask_socketio import SocketIO, emit, join_room, leave_room
from system.rag_system import OptimizedRAGSystem
from system.face_auth import FaceAuthTransformer
from system.voice_service import VoiceService
from config import Config
import os
from dotenv import load_dotenv
import numpy as np
import cv2
import logging
from utils import get_purchase_history
from search_engine.extract_info_image import LLMExtract
from search_engine.get_URL_img import extract_product_images
import sqlite3
import json

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "a_very_secret_key_for_dev_only")
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

config = Config()
rag_system = OptimizedRAGSystem(config)
client_auth_transformers = {}

# Khởi tạo dịch vụ giọng nói
voice_service = VoiceService()
    
logging.basicConfig(level=logging.DEBUG)

def decode_image_from_base64(base64_string):
    """Decodes a base64 image string (data URL) into an OpenCV image."""
    try:
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        img_data = base64.b64decode(base64_string)
        np_arr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        print(f"Error decoding base64 image: {e}")
        return None

# --- Routes ---
@app.route('/')
def index():
    """Serves the main page. Shows auth page if not logged in, chat page otherwise."""

    if session.get('anonymous', False):
        return render_template('chat.html', user_info=None, purchase_history=[])
    elif session.get('authenticated', False) and 'user_info' in session:
        user_info = session.get('user_info')
        purchase_history = []
        if user_info and 'id' in user_info:
            purchase_history = get_purchase_history(user_info['id'])
        return render_template('chat.html', user_info=user_info, purchase_history=purchase_history)
    else:
        return render_template('auto_auth.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Handles incoming chat messages from authenticated or anonymous users."""

    user_key = "anonymous"
    scoped_user_info = None

    if session.get('authenticated', False):
        auth_user_info = session.get('user_info')
        if auth_user_info and 'id' in auth_user_info:
            scoped_user_info = auth_user_info
            user_key = str(scoped_user_info['id'])
        else:
            print("WARNING: Authenticated session but no user_info found. Treating as anonymous.")
            session.pop('authenticated', None)
            session['anonymous'] = True
            user_key = "anonymous"
    elif session.get('anonymous', False):
         user_key = "anonymous"
         scoped_user_info = None
    else:
        print("ERROR: /chat accessed without valid authenticated or anonymous session state.")
        return jsonify({"error": "Invalid session state."}), 403


    data = request.get_json()
    user_query = data.get('prompt')
    if not user_query:
        return jsonify({"error": "No prompt provided"}), 400

    user_query

    try:
        response = rag_system.answer_query(user_key, user_query)
        # Extract product images from the response
        product_images = extract_product_images(response, config.db_path)
        return jsonify({
            "role": "assistant",
            "content": response,
            "product_images": product_images
        })
    except Exception as e:
        print(f"Error getting RAG response: {e}")

        try:
            rag_system.chat_history.add_chat(user_key, user_query, f"ERROR: {e}")
        except Exception as hist_e:
            print(f"Failed to add error to chat history: {hist_e}")
        return jsonify({"error": "Failed to get response from assistant"}), 500

@app.route('/logout')
def logout():
    """Logs the user out by clearing relevant session keys."""


    session.pop('authenticated', None)
    session.pop('user_info', None)
    session.pop('anonymous', None)

    print("Logout completed.")
    return redirect(url_for('index'))

@app.route('/authenticate')
def authenticate():
    """Serves the face authentication page."""

    session.pop('anonymous', None)
    return render_template('auth.html')

@app.route('/start_anonymous_chat')
def start_anonymous_chat():
    """Sets flag for anonymous chat and redirects to index."""

    session.pop('authenticated', None)
    session.pop('user_info', None)
    session.pop('anonymous', None)

    session['anonymous'] = True

    rag_system.clear_chat_history("anonymous")
    print("Starting anonymous chat session.")
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handles displaying and processing the registration form."""
    if request.method == 'GET':
        return render_template('register.html')

    if request.method == 'POST':
        try:
            data = request.get_json()
            name = data.get('name')
            sex = data.get('sex')
            age = data.get('age')
            location = data.get('location')
            images = data.get('images', [])

            if not all([name, sex, age, location]):
                return jsonify({'error': 'Thiếu thông tin bắt buộc'}), 400

            # Kết nối database
            conn = sqlite3.connect('Database.db')
            cursor = conn.cursor()

            # Thêm thông tin người dùng vào bảng Customers
            cursor.execute('''
                INSERT INTO Customers (name, sex, age, location)
                VALUES (?, ?, ?, ?)
            ''', (name, sex, age, location))

            # Lấy ID vừa tạo
            user_id = cursor.lastrowid
            print(f"Đã tạo người dùng mới với ID: {user_id}")

            # Kiểm tra ID có tồn tại trong database
            cursor.execute('SELECT id FROM Customers WHERE id = ?', (user_id,))
            if not cursor.fetchone():
                raise Exception(f"Không tìm thấy người dùng với ID {user_id} trong database")

            # Tạo thư mục lưu ảnh cho người dùng
            user_img_dir = os.path.join('cus_img', str(user_id))
            os.makedirs(user_img_dir, exist_ok=True)
            print(f"Đã tạo thư mục lưu ảnh: {user_img_dir}")

            # Lưu ảnh và tạo embedding
            embeddings = []
            for i, image_data in enumerate(images):
                # Chuyển base64 thành ảnh
                image_data = image_data.split(',')[1]
                image_bytes = base64.b64decode(image_data)

                # Lưu ảnh
                image_path = os.path.join(user_img_dir, f'image_{i+1}.jpg')
                with open(image_path, 'wb') as f:
                    f.write(image_bytes)

                # Tạo embedding
                img = decode_image_from_base64(image_data)
                if img is not None:
                    transformer = FaceAuthTransformer()
                    embedding = transformer.get_face_embedding(img)
                    if embedding is not None:
                        embeddings.append(embedding)

            if embeddings:
                combined_embedding = np.vstack(embeddings)
                embedding_json = json.dumps(combined_embedding.tolist())

                cursor.execute('''
                    UPDATE Customers
                    SET embedding = ?
                    WHERE id = ?
                ''', (embedding_json, user_id))

            conn.commit()
            conn.close()

            return jsonify({'success': True, 'user_id': user_id})

        except Exception as e:
            print(f"Error during registration: {e}")
            return jsonify({'error': 'Lỗi hệ thống'}), 500

@app.route('/reset_session')
def reset_session():
    """Reset session and redirect to auth page."""
    session.pop('authenticated', None)
    session.pop('user_info', None)
    session.pop('anonymous', None)
    return redirect(url_for('index'))

@app.route('/voice-service-status')
def voice_service_status():
    """Check the status of the voice service."""
    status = {
        "available": voice_service.is_available(),
        "api_key_configured": bool(voice_service.api_key),
        "voices": voice_service.get_available_voices()
    }
    return jsonify(status)

@app.route('/text-to-speech', methods=['POST'])
def text_to_speech():
    """Convert text to speech using ElevenLabs API."""
    if not voice_service.is_available():
        return jsonify({"error": "ElevenLabs API key not configured"}), 500

    try:
        data = request.get_json()
        text = data.get('text')
        voice = data.get('voice')  # Tùy chọn: cho phép client chỉ định giọng đọc

        # Sử dụng tốc độ đọc mặc định là 1.0
        speed = 1.2         

        if not text:
            return jsonify({"error": "No text provided"}), 400

        # Giới hạn độ dài văn bản để tránh lỗi từ API
        if len(text) > 5000:
            text = text[:5000]

        # Sử dụng dịch vụ giọng nói để chuyển đổi văn bản thành giọng nói
        audio = voice_service.text_to_speech(text, voice, speed=speed)

        if not audio:
            return jsonify({"error": "No audio data generated"}), 500

        # Chuyển đổi audio thành base64 để gửi về client
        audio_base64 = base64.b64encode(audio).decode('utf-8')

        return jsonify({
            "audio": audio_base64
        })

    except Exception as e:
        return jsonify({"error": f"Failed to generate speech: {str(e)}"}), 500

# --- WebSocket Events ---
@socketio.on('connect')
def handle_connect():
    """Handles new client connections for authentication."""
    sid = request.sid
    print(f'Client connected for auth: {sid}')

    client_auth_transformers[sid] = FaceAuthTransformer()
    join_room(sid)
    print(f"Auth transformer created for SID: {sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """Cleans up when a client disconnects."""
    sid = request.sid
    print(f'Client disconnected: {sid}')

    if sid in client_auth_transformers:
        del client_auth_transformers[sid]
        print(f"Auth transformer removed for SID: {sid}")
    leave_room(sid)

@socketio.on('video_frame')
def handle_video_frame(data):
    """Receives and processes video frames for face authentication."""
    sid = request.sid

    if sid not in client_auth_transformers:
        print(f"Error: No auth transformer found for SID {sid}. Client might need to reconnect.")
        return

    image_data_url = data.get('image')
    if not image_data_url:
        print(f"Error: No image data received from {sid}")
        return

    frame = decode_image_from_base64(image_data_url)
    if frame is None:
        print(f"Error decoding image from {sid}")
        return

    transformer = client_auth_transformers[sid]

    try:
        result = transformer.recognize_face(frame)
        match_outcome = result.get('match')
        bbox = result.get('bbox')
        confidence = result.get('confidence')

        if bbox:
            bbox = [int(coord) for coord in bbox]

        emit_data = {'success': False, 'message': None, 'user_info': None, 'bbox': bbox, 'confidence': confidence}

        if isinstance(match_outcome, dict) and 'id' in match_outcome: # Successful match
            print(f"Authentication successful for SID: {sid}. User: {match_outcome}")
            emit_data['success'] = True
            emit_data['user_info'] = match_outcome
            emit('auth_result', emit_data, room=sid)
        elif match_outcome is False:
            print(f"Authentication explicitly failed for SID: {sid}")
            emit_data['success'] = False
            emit_data['message'] = 'Không nhận dạng được khuôn mặt.'
            emit('auth_result', emit_data, room=sid)
        else:
            emit_data['success'] = False
            emit_data['message'] = 'Đang xử lý...'

            emit('auth_result', emit_data, room=sid)

    except Exception as e:
        print(f"Error during face recognition processing for SID {sid}: {e}")

        emit('auth_result', {'success': False, 'message': f'Lỗi máy chủ: {e}', 'bbox': None, 'confidence': None}, room=sid)

@app.route('/confirm_auth', methods=['POST'])
def confirm_auth():
    """Handles storing session data after successful WebSocket authentication."""
    data = request.get_json()
    user_info = data.get('user_info')

    if not user_info or 'id' not in user_info or 'name' not in user_info:
        return jsonify({'status': 'error', 'message': 'Invalid user info provided'}), 400


    session['authenticated'] = True
    session['user_info'] = user_info
    print(f"Session confirmed for user: {user_info.get('name')}")
    return jsonify({'status': 'ok'})

@app.route('/process_image', methods=['POST'])
def process_image():
    file_path = None
    user_key = "anonymous"
    user_info = None
    purchase_history = []

    if session.get('authenticated', False):
        auth_user_info = session.get('user_info')
        if auth_user_info and 'id' in auth_user_info:
            user_info = auth_user_info
            user_key = str(user_info['id'])
            purchase_history = get_purchase_history(user_info['id'])

    try:
        if not request.content_type.startswith('multipart/form-data'):
            print(f"Unsupported Content-Type for image upload: {request.content_type}")
            return jsonify({'error': 'Invalid request format for image upload'}), 415

        if 'image' not in request.files:
            return jsonify({'error': 'No image file part found'}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        if file:
            save_path = os.path.join('.', file.filename)
            try:
                file.save(save_path)
                file_path = save_path
            except Exception as save_err:
                print(f"Error saving uploaded file: {save_err}")
                return jsonify({'error': 'Could not save uploaded file'}), 500
        else:
            return jsonify({'error': 'Invalid file provided'}), 400

        if not file_path:
             print("Error: file_path is None.")
             return jsonify({'error': 'Internal error determining file path'}), 500

        encoded_image = LLMExtract.image_to_base64(file_path)
        extracted_info = LLMExtract.llm_extract(encoded_image=encoded_image)
        if not extracted_info:
            return jsonify({'error': 'Failed to extract information from image'}), 500


        search_query = f"{extracted_info.ingredients}" \
               f" , màu {extracted_info.drink_color}" \
               f" ,đựng trong {extracted_info.container_type},"


        if extracted_info.topping != 'None':
            search_query += f" {extracted_info.topping}"

        search_query += f".{extracted_info.suitable_for}"

        try:
            search_response = rag_system._answer_with_vector(
                user_key,
                search_query,
                user_info,
                purchase_history,
                is_image_upload=True,
                image_path=file_path
            )

            # Extract product images from the response
            product_images = extract_product_images(search_response, config.db_path)

            if user_key != "anonymous":
                try:
                    rag_system.chat_history.add_chat(user_key, search_query, search_response)
                    print(f"Saved image search history for user: {user_key}")
                except Exception as chat_save_err:
                    print(f"Error saving image search chat history for user {user_key}: {chat_save_err}")

        except Exception as search_err:
            print(f"Exception during vector search: {search_err}")
            if os.path.exists(file_path):
                try: os.remove(file_path)
                except Exception as rm_err: print(f"Error cleaning up file {file_path} after search error: {rm_err}")
            return jsonify({'error': 'Exception during information retrieval'}), 500

        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as rm_err:
                print(f"Error cleaning up file {file_path} after success: {rm_err}")

        return jsonify({
            'content': search_response,
            'product_images': product_images
        })

    except Exception as e:
        print(f"An unexpected error occurred in /process_image: {e}")
        if file_path and os.path.exists(file_path):
             try: os.remove(file_path)
             except Exception as rm_err: print(f"Error cleaning up file {file_path} after unexpected error: {rm_err}")
        return jsonify({'error': 'An unexpected server error occurred'}), 500

if __name__ == '__main__':
    if not os.path.exists('templates'):
        os.makedirs('templates')
    if not os.path.exists('static'):
        os.makedirs('static')

    print(f"Starting Flask-SocketIO server on {config.host}:{config.port}...")
    socketio.run(app, debug=True, host=config.host, port=config.port, use_reloader=False)