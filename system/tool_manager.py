from typing import List, Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
import json

class ToolManager:
    def __init__(self):
        self.tools = self._define_tools()

    def _define_tools(self) -> List[Dict[str, Any]]:
        sql_tool_schema = {
            "name": "use_sql_tool",
            "description": """Sử dụng công cụ này khi truy vấn của người dùng yêu cầu truy xuất, tính toán
                            hoặc tổng hợp dữ liệu có cấu trúc từ cơ sở dữ liệu.
                            Công cụ này phù hợp với các câu hỏi cần số liệu cụ thể, danh sách, tổng, trung bình,
                            đếm số lượng, so sánh, sắp xếp, lọc hoặc thống kê dựa trên dữ liệu trong bảng.
                            Ví dụ: "Tính tổng doanh thu tháng 5", "Liệt kê 3 sản phẩm bán chạy nhất",
                            "Có bao nhiêu đơn hàng", "Sản phẩm nào giá dưới 50k", "So sánh doanh số".
                            KHÔNG sử dụng công cụ này cho các câu hỏi chung, mô tả, hay ý kiến.""",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }

        vector_tool_schema = {
            "name": "use_vector_tool",
            "description": """Sử dụng công cụ này khi truy vấn của người dùng mang tính chung chung, mô tả,
                            giải thích, đưa ra ý kiến, gợi ý hoặc tìm kiếm theo ngữ nghĩa
                            mà KHÔNG yêu cầu tính toán hoặc truy xuất dữ liệu chính xác từ cơ sở dữ liệu.
                            Công cụ này phù hợp với các câu hỏi về mô tả sản phẩm, hướng dẫn sử dụng,
                            thông tin về cửa hàng (nếu không có trong CSDL), lời khuyên chung, hoặc khi câu hỏi
                            mang tính trò chuyện, chào hỏi, hoặc nằm ngoài phạm vi dữ liệu trong DB.
                            Ví dụ: "Trà sữa trân châu đường đen có vị như thế nào?", "Cửa hàng mở cửa mấy giờ?",
                            "Gợi ý đồ uống giải nhiệt", "Chào bạn", "Bạn có thể làm gì?".
                            Sử dụng công cụ này như phương án dự phòng nếu không có công cụ nào khác phù hợp.""",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }

        return [sql_tool_schema, vector_tool_schema]

    def get_tools(self) -> List[Dict[str, Any]]:
        return self.tools

    def create_tool_selection_prompt(self, user_info: dict, recent_history_str: str, query: str, data_schema: str) -> str:
        tools_list_str = "\n".join([f"- {tool['name']}: {tool['description']}" for tool in self.tools])
        
        prompt = f"""
        Bạn là một trợ lý AI chuyên nghiệp. Nhiệm vụ của bạn là phân tích yêu cầu của người dùng và chọn CÔNG CỤ (TOOL) phù hợp nhất để trả lời.
        Dựa vào câu hỏi hiện tại và lịch sử trò chuyện, hãy quyết định xem nên sử dụng công cụ nào trong số các công cụ được cung cấp.
              
        Thông tin người dùng : {user_info}
        Lịch sử trò chuyện gần đây:
        {recent_history_str}

        Câu hỏi của người dùng: {query}

        Các công cụ bạn có thể sử dụng:
        {tools_list_str}

        Cơ sở dữ liệu:
        {data_schema}

        Hãy chọn MỘT công cụ DUY NHẤT phù hợp nhất để trả lời câu hỏi này. Nếu câu hỏi không yêu cầu sử dụng công cụ nào (ví dụ: chào hỏi, cảm ơn đơn thuần), bạn có thể trả lời trực tiếp bằng văn bản.
        """
        return prompt.strip()

    def create_tool_selection_messages(self, prompt: str) -> list:
        return [
            SystemMessage(content="Bạn là một trợ lý AI chuyên nghiệp. Hãy chọn công cụ phù hợp nhất dựa trên câu hỏi của người dùng và lịch sử trò chuyện.\
                          Phải chọn một trong các tool. Không được trả về **additional_kwargs** rỗng. HOẶC Content sử dụng tool nào thì phải trả về tool đó."),
            HumanMessage(content=prompt)
        ]

    def process_tool_response(self, response) -> tuple:
        tool_calls = getattr(response, 'tool_calls', [])
        if not tool_calls:
            return None, {}

        tool_call = tool_calls[0]
        tool_name = None
        args = {}

        if isinstance(tool_call, dict):
            tool_name = tool_call.get("name")
            args = tool_call.get("args", {})
        else:
            tool_name = getattr(tool_call, "name", None)
            args = getattr(tool_call, "args", {})

        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError as e:
                print(f"Lỗi khi parse args JSON: {e}")
                args = {}

        return tool_name, args 