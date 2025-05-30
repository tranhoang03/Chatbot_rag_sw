from typing import List, Optional
from langchain_core.tools import tool
from pydantic import BaseModel

class SQLToolInput(BaseModel):
    """Input for SQL tool - no parameters needed as context is provided separately"""
    pass

class VectorToolInput(BaseModel):
    """Input for Vector tool - no parameters needed as context is provided separately"""
    pass

@tool("use_sql_tool", args_schema=SQLToolInput)
def use_sql_tool() -> str:
    """Sử dụng công cụ này khi truy vấn của người dùng yêu cầu truy xuất, tính toán
    hoặc tổng hợp dữ liệu có cấu trúc từ cơ sở dữ liệu.
    Công cụ này phù hợp với các câu hỏi cần số liệu cụ thể, danh sách, tổng, trung bình,
    đếm số lượng, so sánh, sắp xếp, lọc hoặc thống kê dựa trên dữ liệu trong bảng.
    Ví dụ: "Tính tổng doanh thu tháng 5", "Liệt kê 3 sản phẩm bán chạy nhất",
    "Có bao nhiêu sản phẩm", "Sản phẩm nào giá dưới 50k", "So sánh doanh số".
    KHÔNG sử dụng công cụ này cho các câu hỏi chung, mô tả, hay ý kiến."""
    return "sql_tool_selected"

@tool("use_vector_tool", args_schema=VectorToolInput)
def use_vector_tool() -> str:
    """Sử dụng công cụ này khi truy vấn của người dùng mang tính chung chung, mô tả,
    giải thích, đưa ra ý kiến, gợi ý hoặc tìm kiếm theo ngữ nghĩa
    mà KHÔNG yêu cầu tính toán hoặc truy xuất dữ liệu chính xác từ cơ sở dữ liệu.
    Công cụ này phù hợp với các câu hỏi về mô tả sản phẩm, hướng dẫn sử dụng,
    thông tin về cửa hàng (nếu không có trong CSDL), lời khuyên chung, hoặc khi câu hỏi
    mang tính trò chuyện, chào hỏi, hoặc nằm ngoài phạm vi dữ liệu trong DB.
    Ví dụ: "Trà sữa trân châu đường đen có vị như thế nào?", "Cửa hàng mở cửa mấy giờ?",
    "Gợi ý đồ uống giải nhiệt", "Chào bạn", "Bạn có thể làm gì?".
    Sử dụng công cụ này như phương án dự phòng nếu không có công cụ nào khác phù hợp."""
    return "vector_tool_selected"

class ToolManager:
    def __init__(self):
        self.tools = [use_sql_tool, use_vector_tool]

    def get_tools(self) -> List:
        """Return LangChain tools for binding to LLM"""
        return self.tools

    def create_tool_selection_prompt(self, recent_history_str: str, query: str, data_schema: str) -> str:
        """Create a simplified prompt for tool selection context"""
        prompt = f"""
        Bạn là một trợ lý AI chuyên nghiệp. Hãy phân tích yêu cầu của người dùng và chọn công cụ phù hợp.

        **LỊCH SỬ TRÒ CHUYỆN GẦN ĐÂY:**
        {recent_history_str}

        **CÂU HỎI CỦA NGƯỜI DÙNG:** {query}

        **Cơ sở dữ liệu:**
        {data_schema}

        **HƯỚNG DẪN CHỌN CÔNG CỤ:**
        1. Nếu câu hỏi yêu cầu dữ liệu cụ thể, tính toán, thống kê từ CSDL → chọn use_sql_tool
        2. Nếu câu hỏi mang tính mô tả, gợi ý, trò chuyện chung → chọn use_vector_tool
        3. Kết hợp lịch sử trò chuyện để hiểu ngữ cảnh tốt hơn

        Hãy chọn công cụ phù hợp nhất để trả lời câu hỏi này.   
        """
        return prompt.strip()

    def process_tool_response(self, response) -> Optional[str]:
        """Process LangChain tool response and return tool name"""
        tool_calls = getattr(response, 'tool_calls', [])
        if not tool_calls:
            return None

        tool_call = tool_calls[0]
        if isinstance(tool_call, dict):
            return tool_call.get("name")
        else:
            return getattr(tool_call, "name", None)