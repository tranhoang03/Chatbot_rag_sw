import os
import logging
from elevenlabs import ElevenLabs
import io

logger = logging.getLogger(__name__)

class VoiceService:
    def __init__(self):
        """
        Khởi tạo dịch vụ giọng nói.
        """
        self.api_key = os.environ.get("ELEVENLABS_API_KEY")
        if self.api_key:
            # Khởi tạo client ElevenLabs
            self.client = ElevenLabs(api_key=self.api_key)

            # Lấy danh sách voices có sẵn
            try:
                voices_response = self.client.voices.get_all()
                self.voices = voices_response.voices
            except Exception as e:
                logger.error(f"Lỗi khi lấy danh sách voices: {e}")
                self.voices = []
        else:
            self.client = None
            self.voices = []

        # Mapping tên giọng đọc thân thiện với ID
        self.voice_mapping = {
            "huyen": "foH7s9fX31wFFH2yqrFa",
            "khanhlq": "JYT6xPLD3LGl0ui3YXNq"  
        }

        # Giọng mặc định là Nữ
        self.default_voice_id = "foH7s9fX31wFFH2yqrFa"
        self.default_voice_name = "Nữ"

        # Model mặc định hỗ trợ đa ngôn ngữ
        self.default_model = "eleven_flash_v2_5"

    def is_available(self):

        return self.client is not None

    def text_to_speech(self, text, voice=None, model=None, speed=1.0):
      
        if not self.client:
            logger.error("ElevenLabs API key chưa được cấu hình")
            raise ValueError("ElevenLabs API key chưa được cấu hình")

        if not self.voices:
            logger.error("Không có giọng đọc nào trong tài khoản")
            raise ValueError("Không có giọng đọc nào trong tài khoản")

        try:
            # Xác định voice_id dựa trên tên giọng đọc hoặc sử dụng giọng mặc định
            voice_id = None
            if voice:
                # Tìm voice_id từ tên giọng đọc
                voice_lower = voice.lower()
                if voice_lower in self.voice_mapping:
                    voice_id = self.voice_mapping[voice_lower]
                else:
                    # Tìm voice_id gần đúng
                    for name, id in self.voice_mapping.items():
                        if voice_lower in name:
                            voice_id = id
                            break

            # Nếu không tìm thấy, sử dụng giọng mặc định
            if not voice_id:
                voice_id = self.default_voice_id

            # Sử dụng model mặc định nếu không được chỉ định
            model_id = model or self.default_model


            text = "....... " + text

            # Giới hạn độ dài văn bản để tránh lỗi
            if len(text) > 5000:
                text = text[:5000] + "..."

            # Gọi API ElevenLabs để chuyển đổi văn bản thành giọng nói
            try:
                # Sử dụng API mới của ElevenLabs
                # Cấu hình voice_settings để điều chỉnh tốc độ đọc
                # Đảm bảo tốc độ đọc nằm trong khoảng hợp lệ (0.7 - 1.2)
                adjusted_speed = max(0.7, min(1.2, speed))

                voice_settings = {
                    "stability": 0.5,  # Giá trị mặc định
                    "similarity_boost": 0.75,  # Giá trị mặc định
                    "style": 0.0,  # Giá trị mặc định
                    "use_speaker_boost": True,  # Giá trị mặc định
                    "speed": adjusted_speed  # Tốc độ đọc đã được điều chỉnh
                }

                audio_stream = self.client.text_to_speech.convert(
                    text=text,
                    voice_id=voice_id,
                    model_id=model_id,
                    voice_settings=voice_settings
                )

                # Đọc toàn bộ dữ liệu từ stream
                audio_data = bytes()
                for chunk in audio_stream:
                    audio_data += chunk

                if not audio_data:
                    logger.error("Không nhận được dữ liệu âm thanh từ ElevenLabs API")

                return audio_data

            except Exception as api_error:
                logger.error(f"Lỗi khi gọi ElevenLabs API: {api_error}")

                # Thử lại với văn bản ngắn hơn nếu lỗi có thể do văn bản quá dài
                if len(text) > 1000:
                    # Loại bỏ khoảng dừng đã thêm vào đầu văn bản (", ")
                    if text.startswith(", "):
                        text = text[2:]
                    return self.text_to_speech(text[:1000] + "...", voice, model, speed)
                raise

        except Exception as e:
            logger.error(f"Lỗi khi chuyển đổi văn bản thành giọng nói: {e}")
            raise

    def get_available_voices(self):
        """
        Lấy danh sách các giọng đọc có sẵn.

        Returns:
            dict: Dictionary chứa các giọng đọc có sẵn (tên: id).
        """
        return {
            "Nữ": "foH7s9fX31wFFH2yqrFa",
            "Nam": "JYT6xPLD3LGl0ui3YXNq"
        }
