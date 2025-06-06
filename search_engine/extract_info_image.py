import os
import base64
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from datetime import datetime

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

# ----------------- Khai báo schema thông tin đồ uống ----------------- #
class ExtractedDrinkInfo(BaseModel):
    drink_color: Optional[str] = Field(
        default=None, description="Màu sắc của đồ uống "
    )
    container_type: Optional[str] = Field(
        default=None, description="Loại và hình dáng của cốc hoặc ly "
    )
    ingredients: Optional[str] = Field(
        default=None, description="Thành phần chính"
    )
    topping: Optional[str] = Field(
        default=None, description="Lớp phủ trên đồ uống ."
    )
    suitable_for: Optional[str] = Field(
        default=None, description="Đối tượng hoặc hoàn cảnh thưởng thức lý tưởng"
    )

class LLMExtract:
    @staticmethod 
    def image_to_base64(image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    # ----------------- Hàm mô tả thông tin đồ uống ----------------- #
    def llm_extract(*, encoded_image: Optional[str] = None, url: Optional[str] = None) -> Optional[ExtractedDrinkInfo]:
        if encoded_image is None and url is None:
            print("Image is None.")
            return None

        parser = JsonOutputParser(pydantic_object=ExtractedDrinkInfo)

        # Tạo dict hình ảnh
        image_dict = {"url": url} if url else {"url": f"data:image/jpeg;base64,{encoded_image}"}

        # Prompt tiếng Việt yêu cầu mô tả đồ uống
        prompt = [
            AIMessage(
                content=(
                    "Bạn là một trợ lý thông minh, chuyên trích xuất thông tin có cấu trúc từ ảnh đồ uống.\n\n"
                    "Nhiệm vụ của bạn là phân tích kỹ ảnh đồ uống tôi cung cấp và trích xuất các thông tin sau:\n"
                    "1. **drink_color**: Màu sắc của đồ uống(mô tả chi tiết màu sắc)\n"
                    "2. **container_type**: Hình dáng và kiểu dáng của cốc hoặc ly(Ví dụ: cốc nhựa, cốc thủy tinh,...)\n"
                    "3. **ingredients**: Thành phần chính(Ví dụ: sữa, đường, trân châu, đá,...)\n"
                    "4. **topping**: Lớp phủ nếu có(Ví dụ: kem béo, trân châu, thạch,...). Nếu KHÔNG có lớp phủ trả về **None**.\n"
                    "5. **suitable_for**: Đối tượng hoặc hoàn cảnh thưởng thức lý tưởng\n\n"
                    "👉 Yêu cầu:\n"
                    "- Tất cả thông tin phải được viết bằng **tiếng Việt**\n"
                    "- Nếu không có thông tin, hãy ghi rõ `không có topping`.\n"
                    "- Trả lời đúng theo định dạng JSON sau:\n"
                    f"{parser.get_format_instructions()}\n"
                    "Chỉ trả lời dưới dạng JSON, không kèm giải thích."
                )
            ),
            HumanMessage(
                content=[
                    {"type": "text", "text": "Trích xuất thông tin đồ uống trong ảnh này."},
                    {"type": "image_url", "image_url": image_dict}
                ]
            ),
        ]

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("GOOGLE_API_KEY is not set.Check .env file.")
            return None

        llm = ChatGoogleGenerativeAI(
            model=os.getenv("GOOGLE_GENAI_MODEL", "gemini-1.5-flash-latest"),
            temperature=float(os.getenv("GOOGLE_GENAI_TEMPERATURE", 0)),
            google_api_key=api_key
        )

        try:
            response = llm.invoke(prompt)
            data = parser.parse(response.content)
            return ExtractedDrinkInfo(**data)
        except Exception as e:
            print(f"Error response from model: {e}")
            return None
