from typing import List, Tuple, Dict, Any
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import json
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
import sqlite3
from langchain_core.output_parsers import StrOutputParser
from langchain_core.embeddings import Embeddings
from transformers import AutoModel, AutoTokenizer
import torch
from config import Config
from utils import (
    load_table_data,
    execute_sql_query,
    format_sql_results,
    validate_sql_query,
    get_purchase_history
)
from .chat_history import ChatHistory
from .prompts import PromptManager
from search_engine.feature_extractor import ImageFeatureExtractor
from search_engine.faiss_indexer import FaissIndexer
from search_engine.hybrid_search import HybridSearchResult
import faiss
from .tool_manager import ToolManager
from .embeddings import PhoBERTEmbeddings

class OptimizedRAGSystem:
    def __init__(self, config: Config):
        self.config = config
        self.chat_history = ChatHistory()
        self.tool_manager = ToolManager()
        self._initialize_components()

    def _initialize_components(self):
        """Khởi tạo các thành phần chính"""
        self.embeddings = PhoBERTEmbeddings()

        self.llm = ChatGoogleGenerativeAI(
            model=self.config.llm_model,
            temperature=self.config.llm_temperature,
            google_api_key=self.config.google_api_key
        )

        self.vector_store = self._initialize_vector_store()
        self.description_vector_store = self._initialize_description_vector_store()

    def _initialize_vector_store(self) -> FAISS:
        """Load vector store or create new if not found"""
        if os.path.exists(self.config.vector_store_path):
            try:
                return FAISS.load_local(
                    self.config.vector_store_path,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
            except Exception as e:
                print(f"Error loading vector store: {e}")
                return self._create_new_vector_store()
        return self._create_new_vector_store()

    def _create_new_vector_store(self) -> FAISS:
        """Create a new FAISS vector store"""
        try:
            os.makedirs(self.config.vector_store_path, exist_ok=True)
            documents = load_table_data(self.config.db_path)
            if not documents:
                print("No documents loaded from database")
                return None
            texts = [doc["content"] for doc in documents]
            metadatas = [doc["metadata"] for doc in documents]

            print(f"Creating vector store with {len(texts)} documents")
            vector_store = FAISS.from_texts(
                texts=texts,
                embedding=self.embeddings,
                metadatas=metadatas
            )
            vector_store.save_local(self.config.vector_store_path)
            print("Vector store created and saved successfully")
            return vector_store

        except Exception as e:
            print(f"Error creating vector store: {e}")
            return None

    def _initialize_description_vector_store(self) -> FAISS:
        """Initialize or create description vector store"""
        if os.path.exists(self.config.description_vector_store_path):
            try:
                return FAISS.load_local(
                    self.config.description_vector_store_path,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
            except Exception as e:
                print(f"Error loading description vector store: {e}")
                return self._create_description_vector_store()
        return self._create_description_vector_store()

    def _create_description_vector_store(self) -> FAISS:
        """Create FAISS vector store for product descriptions"""
        try:
            os.makedirs(self.config.description_vector_store_path, exist_ok=True)
            conn = sqlite3.connect(self.config.db_path)
            cursor = conn.cursor()
            cursor.execute("""SELECT Product.ID,Name_Product, Descriptions
                           FROM Product ;""")
            products = cursor.fetchall()
            conn.close()
            if not products:
                print("No product descriptions found.")
                return None
            print(f"Số sản phẩm được vector hóa: {len(products)}")
            descriptions = [
                f"{product[2]}" for product in products
            ]
            metadatas = [
                {"ID":product[0],"name": product[1], "description": product[2]} for product in products
            ]

            vector_store = FAISS.from_texts(
                texts=descriptions,
                embedding=self.embeddings,
                metadatas=metadatas
            )
            vector_store.save_local(self.config.description_vector_store_path)
            print("Description vector store created and saved successfully.")
            return vector_store

        except Exception as e:
            print(f"Error creating description vector store: {e}")
            return None



    def _get_database_schema(self) -> str:
        """Get database schema information with descriptions"""
        try:
            conn = sqlite3.connect(self.config.db_path)
            cursor = conn.cursor()

            # Định nghĩa mô tả cho từng bảng
            table_descriptions = {
                    "order": "Lưu thông tin đơn hàng của khách hàng",
                    "product": "Chứa thông tin về tên, mô tả về thành phần, màu sắc đồ uống,... và hình ảnh của các sản phẩm đang bán",
                    "variant": "Chứa thông tin chi tiết về từng biến thể của một sản phẩm đồ uống như kích cỡ, hàm lượng dinh dường, giá, hạng bán ra.",
                    "categories": "Lưu danh sách các danh mục phân loại sản phẩm đồ uống. Mỗi danh mục tương ứng với một nhóm sản phẩm cùng loại (ví dụ: cà phê, trà, nước ép).",
            }

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()

            schema_info = []
            for table in tables:
                table_name = table[0]

                # Bỏ qua bảng customers
                if table_name.lower() in ["customers"]:
                    continue

                # Lấy thông tin schema
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()

                cursor.execute(f"PRAGMA foreign_key_list({table_name})")
                foreign_keys = cursor.fetchall()

                cursor.execute(f"PRAGMA index_list({table_name})")
                indexes = cursor.fetchall()

                # Format column information
                column_info = []
                for col in columns:
                    col_name = col[1]
                    col_type = col[2]
                    is_pk = col[5] == 1
                    pk_info = " (PRIMARY KEY)" if is_pk else ""
                    column_info.append(f"{col_name} ({col_type}){pk_info}")

                # Format foreign key information
                fk_info = []
                for fk in foreign_keys:
                    ref_table = fk[2]
                    from_col = fk[3]
                    to_col = fk[4]
                    fk_info.append(f"FOREIGN KEY ({from_col}) REFERENCES {ref_table}({to_col})")

                # Format index information
                index_info = []
                for idx in indexes:
                    idx_name = idx[1]
                    is_unique = idx[2] == 1
                    if not idx_name.startswith('sqlite_autoindex'):
                        index_info.append(f"{'UNIQUE ' if is_unique else ''}INDEX {idx_name}")

                # Mô tả bảng (nếu có)
                description = table_descriptions.get(table_name.lower(), "Không có mô tả.")
                table_info = [f"Bảng {table_name}: {description}"]
                table_info.extend(column_info)
                if fk_info:
                    table_info.append("\nKhóa ngoại:")
                    table_info.extend(fk_info)
                if index_info:
                    table_info.append("\nChỉ mục:")
                    table_info.extend(index_info)

                schema_info.append("\n".join(table_info))

            conn.close()
            return "\n\n".join(schema_info)

        except Exception as e:
            print(f"Error getting database schema: {e}")
            return ""


    def _answer_with_vector(self, user_key: str, query: str, user_info: dict, purchase_history: list, is_image_upload: bool = False, image_path: str = None) -> str:
        """Answer query using vector search, with a special prompt for image uploads"""
        try:
            print("\n=== Bắt đầu tìm kiếm ===")
            print(f"Query: {query}")
            print(f"Image path: {image_path}")
            print(f"Is image upload: {is_image_upload}")

            # Chọn vector store phù hợp
            if is_image_upload:
                if not self.description_vector_store:
                    return "Không thể tìm kiếm vì vector store mô tả chưa sẵn sàng."
                vector_store = self.description_vector_store
            else:
                vector_store = self.vector_store

            # Tìm kiếm dựa trên mô tả văn bản
            print("\n=== Tìm kiếm dựa trên mô tả văn bản ===")
            text_docs = vector_store.similarity_search_with_score(
                query,
                k=self.config.top_k_results
            )
            print(f"Số kết quả tìm kiếm văn bản: {len(text_docs)}")
            for i, (doc, score) in enumerate(text_docs):
                print(f"\nKết quả văn bản {i+1}:")
                print(f"Metadata: {doc.metadata}")
                print(f"Content: {doc.page_content}")
                print(f"Score: {score}")

            # Nếu là tìm kiếm ảnh, thêm tìm kiếm dựa trên đặc trưng ảnh
            if is_image_upload and image_path:
                print("\n=== Tìm kiếm dựa trên đặc trưng ảnh ===")
                # Khởi tạo hybrid search
                hybrid_search = HybridSearchResult(self.config)

                # Tìm kiếm dựa trên đặc trưng ảnh
                image_results = hybrid_search.search_by_image_features(
                    image_path,  # Sử dụng đường dẫn ảnh upload
                    k=self.config.top_k_results
                )
                print(f"Số kết quả tìm kiếm ảnh: {len(image_results)}")
                for i, (meta, dist) in enumerate(image_results):
                    print(f"\nKết quả ảnh {i+1}:")
                    print(f"Metadata: {meta}")
                    print(f"Distance: {dist}")

                # Chuẩn hóa metadata từ kết quả văn bản
                text_results = []
                for doc, score in text_docs:
                    # Lấy product_id từ metadata của văn bản
                    product_id = doc.metadata.get('ID')
                    if product_id:
                        # Lấy thông tin sản phẩm từ database
                        product_info = hybrid_search._get_product_info(product_id)
                        if product_info:
                            text_results.append({
                                'product_id': product_id,
                                'name': product_info['name'],
                                'description': product_info['description'],
                                'price': product_info['price'],
                                'score': score
                            })

                # Chuẩn hóa metadata từ kết quả ảnh
                image_results_normalized = []
                for meta, dist in image_results:
                    product_id = meta.get('product_id')
                    if product_id:

                        product_info = hybrid_search._get_product_info(product_id)
                        if product_info:
                            image_results_normalized.append(({
                                'product_id': product_id,
                                'name': product_info['name'],
                                'description': product_info['description'],
                                'price': product_info['price'],
                            }, dist))

                # Kết hợp kết quả từ hai phương pháp
                combined_results = hybrid_search.combine_results_mbr(
                    text_results=text_results,
                    image_results=image_results_normalized,
                    alpha=0.5,
                    k=self.config.top_k_results
                )
                print(f"Số kết quả sau khi kết hợp: {len(combined_results)}")
                for i, result in enumerate(combined_results):
                    print(f"\nKết quả kết hợp {i+1}:")
                    print(f"Metadata: {result}")

                # Tạo context từ kết quả kết hợp với rank
                context = []
                for i, result in enumerate(combined_results):
                    # Lấy product_id từ kết quả
                    product_id = result.get('product_id')
                    # Lấy thông tin chi tiết sản phẩm với giá các biến thể
                    detailed_info = hybrid_search._get_product_info(product_id)
                    # Thêm thông tin vào context
                    context.append(f"Rank {i+1}: Tên: {detailed_info['name']}, Mô tả: {detailed_info['description']}, Giá: {detailed_info['variant_prices']}")
            else:
                # Tạo context từ kết quả văn bản với rank
                context = []
                for i, (doc, score) in enumerate(text_docs):
                    # Lấy product_id từ metadata
                    product_id = doc.metadata.get('ID')
                    if product_id:
                        # Khởi tạo hybrid search để lấy thông tin chi tiết sản phẩm
                        hybrid_search = HybridSearchResult(self.config)
                        # Lấy thông tin chi tiết sản phẩm với giá các biến thể
                        detailed_info = hybrid_search._get_product_info(product_id)
                        # Thêm thông tin vào context
                        context.append(f"Rank {i+1}: Tên: {detailed_info['name']}, Mô tả: {detailed_info['description']}, Giá: {detailed_info['variant_prices']}")
                    else:
                        # Trường hợp hiếm gặp khi không có product_id
                        context.append(f"Rank {i+1}: {doc.page_content}")

            recent_history = self.chat_history.get_latest_chat(user_key)

            if is_image_upload:
                prompt = PromptManager.get_image_upload_prompt(context, query, recent_history, user_info)
            else:
                prompt = PromptManager.get_vector_prompt(context, query, recent_history, user_info, purchase_history)

            print("\n=== Prompt gửi cho LLM ===")
            print(prompt)
            response = self.llm.invoke(prompt)

            return getattr(response, "content", str(response)).strip()

        except Exception as e:
            print(f"\n=== Lỗi xảy ra ===")
            print(f"Error: {str(e)}")
            return f"Lỗi khi xử lý câu hỏi: {str(e)}"


    def _answer_with_sql(self, user_key: str, query: str, user_info: dict, purchase_history: list) -> str:
        """Answer query using SQL"""
        try:
            # Lấy đoạn chat gần nhất
            latest_chat = self.chat_history.get_latest_chat(user_key)

            sql_prompt = PromptManager.get_sql_generation_prompt(
                query=query,
                schema_info=self._get_database_schema(),
                history=latest_chat
            )
            sql_query_response = self.llm.invoke(sql_prompt)

            sql_query_string = sql_query_response.content.strip() if hasattr(sql_query_response, 'content') else str(sql_query_response).strip()

            if sql_query_string.startswith("```") and sql_query_string.endswith("```"):
                sql_query_string = "\n".join(sql_query_string.splitlines()[1:-1]).strip()
            print("Generated SQL query:", sql_query_string)

            if not validate_sql_query(sql_query_string):
                return "Xin lỗi, tôi không thể thực hiện truy vấn này vì lý do an toàn hoặc truy vấn không hợp lệ."

            results = execute_sql_query(
                self.config.db_path,
                sql_query_string,
                self.config.db_timeout
            )


            formatted_results = format_sql_results(results)
            recent_history = self.chat_history.get_latest_chat(user_key)

            response_prompt = PromptManager.get_sql_response_prompt(
                query=query,
                results=formatted_results,
                history=recent_history,
                user_info=user_info,
                purchase_history=purchase_history
            )
            print(response_prompt)
            final_response = self.llm.invoke(response_prompt)
            return final_response.content.strip() if hasattr(final_response, 'content') else str(final_response).strip()

        except Exception as e:
            print(f"Error during SQL processing: {e}")
            return f"Lỗi khi xử lý câu hỏi liên quan đến SQL: {str(e)}"


    def answer_query(self, user_key: str, query: str) -> str:
        """Process query and return answer using function calling"""
        try:
            print(f"Processing query: {query} for user: {user_key}")

            user_info = self._get_user_info(user_key)
            data_schema = self._get_database_schema()
            recent_history_str = self.chat_history.get_latest_chat(user_key)
            purchase_history = get_purchase_history(user_key)

            prompt = self.tool_manager.create_tool_selection_prompt(
                user_info=user_info,
                recent_history_str=recent_history_str,
                query=query,
                data_schema=data_schema
            )

            messages = self.tool_manager.create_tool_selection_messages(prompt)

            print("Invoking LLM for tool selection...")
            response = self.llm.invoke(messages, tools=self.tool_manager.get_tools())
            print(f"LLM Response: {response}")

            final_response = ""

            tool_name, args = self.tool_manager.process_tool_response(response)
            print(f"Tool name: {tool_name}, Args: {args}")

            if tool_name == "use_sql_tool":
                final_response = self._answer_with_sql(user_key, query, user_info, purchase_history)
            elif tool_name == "use_vector_tool":
                is_image_upload = False
                final_response = self._answer_with_vector(user_key, query, user_info, purchase_history, is_image_upload)
            else:
                final_response = "Xin lỗi, tôi không hiểu yêu cầu này hoặc công cụ được gọi không hợp lệ."
                print(f"Unknown tool name: '{tool_name}'")

            self.chat_history.add_chat(user_key, query, final_response)
            return final_response

        except Exception as e:
            error_msg = f"Lỗi hệ thống khi xử lý yêu cầu: {str(e)}"
            print(f"Error in answer_query: {error_msg}")
            self.chat_history.add_chat(user_key, query, error_msg)
            return error_msg


    def _get_user_info(self, user_key: str) -> dict:
        """Fetch user information based on user key"""
        if user_key == "anonymous":
            return None

        try:

            db_path = os.path.join(os.path.dirname(__file__), '..', 'Database.db')
            if not os.path.exists(db_path):
                db_path = os.path.join(os.path.dirname(__file__), 'Database.db')
                if not os.path.exists(db_path):
                    print(f"Database file not found at expected locations.")
                    return None

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            query = "SELECT id, name, sex FROM Customers WHERE id = ?"
            cursor.execute(query, (user_key,))
            result = cursor.fetchone()
            conn.close()

            if result:
                return {"id": result[0], "name": result[1], "sex": result[2]}
            else:
                print(f"User with ID {user_key} not found.")
                return None
        except Exception as e:
            print(f"Error fetching user info for user {user_key}: {e}")
            return None
    def clear_chat_history(self, user_key: str):
        """Clears the chat history for a specific user key."""
        try:
            self.chat_history.clear_history(user_key)
        except Exception as e:
            print(f"Error clearing chat history for {user_key}: {e}")

    def _initialize_description_vector_store(self) -> FAISS:
        """Initialize description vector store if exists, otherwise create it"""
        if os.path.exists(self.config.description_vector_store_path):
            try:
                return FAISS.load_local(
                    self.config.description_vector_store_path,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
            except Exception as e:
                print(f"Error loading description vector store: {e}")

        return self._create_description_vector_store()
