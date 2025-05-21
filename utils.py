import json
import sqlite3
from typing import List, Dict, Any, Tuple
import base64
import os
import re
from pathlib import Path
from sqlglot import parse_one, errors
def load_table_data(db_path: str) -> List[Dict[str, Any]]:
    """Load data from all tables in the database and format for vector store"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        documents = []

        column_name_mapping = {
            # Bảng Categories
            "Id": "id danh mục",
            "Name_Cat": "tên danh mục",
            "Description": "mô tả danh mục",

            # Bảng Product
            "Categories_id": "id danh mục",
            # "Id": "id sản phẩm",
            "Name_Product": "tên sản phẩm",
            "Descriptions": "mô tả sản phẩm",
            "Link_Image": "link ảnh",
            # Bảng Variant
            "Beverage Option": "tùy chọn đồ uống",
            "Calories": "calo",
            "Dietary_Fibre_g": "chất xơ",
            "Sugars_g": "đường",
            "Protein_g": "protein",
            "Vitamin_A": "vitamin A",
            "Vitamin_C": "vitamin C",
            "Caffeine_mg": "caffeine",
            "Price": "đơn giá",
            "Sales_rank": "bán chạy",
            # Bảng Store
            # "Id": "id cửa hàng",
             "Name_Store": "tên cửa hàng",
            "Address": "địa chỉ",
            "Phone": "số điện thoại",
            "Open_Close": "giờ mở cửa đóng cửa",

            # Bảng Orders
            # "Id": "id đơn hàng",
            "Customer_id": "id khách hàng",
            "Store_id": "id cửa hàng",
            "Order_date": "ngày đặt hàng",

            # Bảng Order_detail
            "Order_id": "id đơn hàng",
            "Product_id": "id sản phẩm",
            "Quantity": "số lượng",
            "Price": "đơn giá",
            "Rate": "đánh giá", # Hoặc "đánh giá"

            # Bảng Customer_preferences

            "Preferred_categories": "danh mục ưa thích",
            "Max_price": "giá tối đa",

            # Bảng customers
            "id": "id khách hàng",
            "name": "tên khách hàng",
            "sex": "giới tính",
            "age": "tuổi",
            "location": "địa chỉ",
            "picture": "ảnh",
            "embedding": "embedding"
        }

        print("\n=== Loading Data for Vector Store ===")
        for table_tuple in tables:
            table_name = table_tuple[0]
            print(f"Processing table: {table_name}")


            if table_name == 'sqlite_sequence':
                continue

            cursor.execute(f"PRAGMA table_info({table_name});")
            columns_info = cursor.fetchall()
            column_names = [col[1] for col in columns_info]

            cursor.execute(f"SELECT * FROM {table_name};")
            rows = cursor.fetchall()

            print(f"  - Found {len(rows)} rows")

            # Convert each row to a document
            for row_idx, row in enumerate(rows):
                # Create a dictionary of column names and values
                row_dict = {}
                for col_name, val in zip(column_names, row):
                    if (table_name == "customers" and col_name in ["embedding", "picture"]) or \
                       (table_name == "Product" and col_name == "Link_Image"):
                        continue
                    row_dict[col_name] = val

                content_parts = []
                for k, v in row_dict.items():
                    display_name = column_name_mapping.get(k, k)
                    value_str = str(v) if v is not None else "không có"
                    content_parts.append(f"{display_name}: {value_str}")

                content = f"Bảng {table_name}: " + ", ".join(content_parts)

                metadata = {
                    "table": table_name,
                     "columns": list(row_dict.keys()),
                    "data": row_dict,
                    "original_row_index": row_idx
                }

                documents.append({
                    "content": content,
                    "metadata": metadata
                })

        print("\n=== Summary ===")
        print(f"Total documents created: {len(documents)}")
        print("="*50)

        conn.close()
        return documents

    except Exception as e:
        print(f"Error loading table data: {e}")
        return []



def execute_sql_query(db_path: str, query: str, timeout: int = 30) -> List[Dict[str, Any]]:
    """Execute SQL query and return results"""
    try:
        conn = sqlite3.connect(db_path, timeout=timeout)
        cursor = conn.cursor()

        cursor.execute(query)


        columns = [description[0] for description in cursor.description]

        rows = cursor.fetchall()

        results = []
        for row in rows:
            result_dict = dict(zip(columns, row))
            results.append(result_dict)

        conn.close()
        return results

    except Exception as e:
        print(f"Error executing SQL query: {e}")
        return []

def format_sql_results(results: List[Dict[str, Any]]) -> str:
    """Format SQL results into a readable string"""
    if not results:
        return "Không tìm thấy kết quả"

    formatted_results = []
    for result in results:

        result_str = ", ".join([
            f"{k}: {v}" for k, v in result.items()
        ])
        formatted_results.append(result_str)

    return "\n".join(formatted_results)



def validate_sql_query(query: str) -> bool:
    """Validate SELECT SQL query using SQLGlot parser."""

    def log_invalid(reason: str) -> bool:
        print(f"Validation failed: {reason}")
        return False

    try:
        query = query.strip()
        if not query:
            return log_invalid("Empty query")

        # Remove trailing semicolon
        if query.endswith(";"):
            query = query[:-1].strip()

        # Kiểm tra các từ khóa nguy hiểm trước
        query_upper = query.upper()
        dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]
        if any(kw in query_upper for kw in dangerous_keywords):
            return log_invalid("Dangerous keyword found")

        # Kiểm tra xem có phải là câu SELECT không
        if not query_upper.startswith("SELECT"):
            return log_invalid("Only SELECT queries are allowed")

        # Thử parse query bằng sqlglot
        try:
            ast = parse_one(query)
            if ast is None:
                return log_invalid("Could not parse query")
        except errors.ParseError:
            # Nếu không parse được, kiểm tra thêm một số trường hợp đặc biệt
            if "LIKE" in query_upper and "%" in query:
                # Cho phép các câu LIKE với %
                pass
            elif ("[" in query and "]" in query) or ("`" in query):
                # Cho phép các tên cột có khoảng trắng được đặt trong [] hoặc ``
                pass
            elif " AS " in query_upper:
                # Cho phép sử dụng alias với AS
                pass
            elif "JOIN" in query_upper:
                # Cho phép các câu JOIN
                pass
            else:
                return log_invalid("Invalid SQL syntax")

        print("Query validation passed ✅")
        return True

    except Exception as e:
        return log_invalid(f"Unexpected error: {e}")



def get_purchase_history(user_id: int) -> list:
    """Fetches the last 5 purchase history items for a given user ID."""
    try:
        BASE_DIR = Path(os.path.dirname(__file__))
        db_path = os.path.join(BASE_DIR, 'Database.db')
        if not os.path.exists(db_path):
             db_path = os.path.join(os.path.dirname(__file__), 'Database.db')
             if not os.path.exists(db_path):
                 print(f"Database file not found at expected locations.")
                 return []

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        query = """
                SELECT o.Order_date, p.Name_Product || ' ' || [Beverage Option], od.Quantity, (v.Price * od.Quantity) AS Price, od.Rate
                FROM Orders o
                JOIN Order_detail od ON o.Id = od.Order_id
                JOIN Variant v ON od.Variant_id = v.Id
                JOIN Product p ON v.Product_id = p.Id
                WHERE o.Customer_id = ?
                ORDER BY o.Order_date DESC
                LIMIT 5
        """

        cursor.execute(query, (user_id,))
        results = cursor.fetchall()
        conn.close()
        history = [
            {"date": row[0], "product": row[1], "quantity": row[2], "price": row[3], "rate": row[4]}
            for row in results
        ]
        return history
    except Exception as e:
        print(f"Error getting purchase history for user {user_id}: {e}")
        return []

def get_all_categories(db_path: str) -> List[Dict[str, Any]]:
    """Get all product categories from the database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = "SELECT Id, Name_Cat, Description FROM Categories ORDER BY Name_Cat"
        cursor.execute(query)
        results = cursor.fetchall()

        conn.close()

        categories = [
            {"id": row[0], "name": row[1], "description": row[2]}
            for row in results
        ]

        return categories
    except Exception as e:
        print(f"Error getting categories: {e}")
        return []

def get_products_by_category(db_path: str, category_id: int) -> List[Dict[str, Any]]:
    """Get products by category ID."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = """
            SELECT p.Id, p.Name_Product, p.Descriptions, c.Name_Cat
            FROM Product p
            JOIN Categories c ON p.Categories_id = c.Id
            WHERE p.Categories_id = ?
            ORDER BY p.Name_Product
        """

        cursor.execute(query, (category_id,))
        results = cursor.fetchall()

        conn.close()

        products = [
            {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "category": row[3]
            }
            for row in results
        ]

        return products
    except Exception as e:
        print(f"Error getting products by category: {e}")
        return []

def get_all_products(db_path: str) -> List[Dict[str, Any]]:
    """Get all products with their categories."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = """
            SELECT p.Id, p.Name_Product, p.Descriptions, c.Name_Cat, c.Id
            FROM Product p
            JOIN Categories c ON p.Categories_id = c.Id
            ORDER BY c.Name_Cat, p.Name_Product
        """

        cursor.execute(query)
        results = cursor.fetchall()

        conn.close()

        products = [
            {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "category": row[3],
                "category_id": row[4]
            }
            for row in results
        ]

        return products
    except Exception as e:
        print(f"Error getting all products: {e}")
        return []
