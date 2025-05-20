import sqlite3
from typing import Dict, List, Any, Optional
from config import Config

class MenuService:
    """Service class for handling menu-related operations"""

    def __init__(self, config: Config):
        self.config = config
        self.db_path = config.db_path
        self.predefined_queries = self._initialize_predefined_queries()

    def _initialize_predefined_queries(self) -> Dict:
        """Initialize predefined SQL queries for menu categories and products"""
        return {
            # Tất cả danh mục
            'menu_categories': {
                'sql': """
                    SELECT c.Id, c.Name_Cat, c.Description, COUNT(p.Id) as product_count
                    FROM Categories c
                    JOIN Product p ON c.Id = p.Categories_id
                    GROUP BY c.Id
                    ORDER BY c.Name_Cat
                """,
                'format_function': lambda results: {
                    "type": "categories",
                    "title": "Danh mục đồ uống",
                    "items": [
                        {
                            "id": item["Id"],
                            "name": item["Name_Cat"],
                            "description": item["Description"],
                            "count": item["product_count"]
                        } for item in results
                    ]
                }
            },

            # Classic Espresso Drinks
            'classic_espresso': {
                'sql': """
                    SELECT p.Id, p.Name_Product, p.Descriptions, c.Name_Cat
                    FROM Product p
                    JOIN Categories c ON p.Categories_id = c.Id
                    WHERE c.Name_Cat = 'Classic Espresso Drinks'
                    ORDER BY p.Name_Product
                """,
                'format_function': lambda results: {
                    "type": "products",
                    "title": "Classic Espresso Drinks",
                    "items": [
                        {
                            "id": item["Id"],
                            "name": item["Name_Product"],
                            "description": item["Descriptions"],
                            "category": item["Name_Cat"]
                        } for item in results
                    ]
                }
            },

            # Coffee
            'coffee': {
                'sql': """
                    SELECT p.Id, p.Name_Product, p.Descriptions, c.Name_Cat
                    FROM Product p
                    JOIN Categories c ON p.Categories_id = c.Id
                    WHERE c.Name_Cat = 'Coffee'
                    ORDER BY p.Name_Product
                """,
                'format_function': lambda results: {
                    "type": "products",
                    "title": "Coffee",
                    "items": [
                        {
                            "id": item["Id"],
                            "name": item["Name_Product"],
                            "description": item["Descriptions"],
                            "category": item["Name_Cat"]
                        } for item in results
                    ]
                }
            },

            # Frappuccino Blended Coffee
            'frappuccino_coffee': {
                'sql': """
                    SELECT p.Id, p.Name_Product, p.Descriptions, c.Name_Cat
                    FROM Product p
                    JOIN Categories c ON p.Categories_id = c.Id
                    WHERE c.Name_Cat = 'Frappuccino Blended Coffee'
                    ORDER BY p.Name_Product
                """,
                'format_function': lambda results: {
                    "type": "products",
                    "title": "Frappuccino Blended Coffee",
                    "items": [
                        {
                            "id": item["Id"],
                            "name": item["Name_Product"],
                            "description": item["Descriptions"],
                            "category": item["Name_Cat"]
                        } for item in results
                    ]
                }
            },

            # Frappuccino Blended Crème
            'frappuccino_creme': {
                'sql': """
                    SELECT p.Id, p.Name_Product, p.Descriptions, c.Name_Cat
                    FROM Product p
                    JOIN Categories c ON p.Categories_id = c.Id
                    WHERE c.Name_Cat = 'Frappuccino Blended Crème'
                    ORDER BY p.Name_Product
                """,
                'format_function': lambda results: {
                    "type": "products",
                    "title": "Frappuccino Blended Crème",
                    "items": [
                        {
                            "id": item["Id"],
                            "name": item["Name_Product"],
                            "description": item["Descriptions"],
                            "category": item["Name_Cat"]
                        } for item in results
                    ]
                }
            },

            # Shaken Iced Beverages
            'iced_beverages': {
                'sql': """
                    SELECT p.Id, p.Name_Product, p.Descriptions, c.Name_Cat
                    FROM Product p
                    JOIN Categories c ON p.Categories_id = c.Id
                    WHERE c.Name_Cat = 'Shaken Iced Beverages'
                    ORDER BY p.Name_Product
                """,
                'format_function': lambda results: {
                    "type": "products",
                    "title": "Shaken Iced Beverages",
                    "items": [
                        {
                            "id": item["Id"],
                            "name": item["Name_Product"],
                            "description": item["Descriptions"],
                            "category": item["Name_Cat"]
                        } for item in results
                    ]
                }
            },

            # Signature Espresso Drinks
            'signature_espresso': {
                'sql': """
                    SELECT p.Id, p.Name_Product, p.Descriptions, c.Name_Cat
                    FROM Product p
                    JOIN Categories c ON p.Categories_id = c.Id
                    WHERE c.Name_Cat = 'Signature Espresso Drinks'
                    ORDER BY p.Name_Product
                """,
                'format_function': lambda results: {
                    "type": "products",
                    "title": "Signature Espresso Drinks",
                    "items": [
                        {
                            "id": item["Id"],
                            "name": item["Name_Product"],
                            "description": item["Descriptions"],
                            "category": item["Name_Cat"]
                        } for item in results
                    ]
                }
            },

            # Smoothies
            'smoothies': {
                'sql': """
                    SELECT p.Id, p.Name_Product, p.Descriptions, c.Name_Cat
                    FROM Product p
                    JOIN Categories c ON p.Categories_id = c.Id
                    WHERE c.Name_Cat = 'Smoothies'
                    ORDER BY p.Name_Product
                """,
                'format_function': lambda results: {
                    "type": "products",
                    "title": "Smoothies",
                    "items": [
                        {
                            "id": item["Id"],
                            "name": item["Name_Product"],
                            "description": item["Descriptions"],
                            "category": item["Name_Cat"]
                        } for item in results
                    ]
                }
            },

            # Tazo Tea Drinks
            'tea': {
                'sql': """
                    SELECT p.Id, p.Name_Product, p.Descriptions, c.Name_Cat
                    FROM Product p
                    JOIN Categories c ON p.Categories_id = c.Id
                    WHERE c.Name_Cat = 'Tazo Tea Drinks'
                    ORDER BY p.Name_Product
                """,
                'format_function': lambda results: {
                    "type": "products",
                    "title": "Tazo Tea Drinks",
                    "items": [
                        {
                            "id": item["Id"],
                            "name": item["Name_Product"],
                            "description": item["Descriptions"],
                            "category": item["Name_Cat"]
                        } for item in results
                    ]
                }
            }
        }

    def get_question_for_query_id(self, query_id: str) -> str:
        """Get the corresponding question for a query ID"""
        question_map = {
            'menu_categories': 'Cho tôi xem danh mục đồ uống',
            'classic_espresso': 'Cho tôi xem các loại Classic Espresso Drinks',
            'coffee': 'Cho tôi xem các loại Coffee',
            'frappuccino_coffee': 'Cho tôi xem các loại Frappuccino Blended Coffee',
            'frappuccino_creme': 'Cho tôi xem các loại Frappuccino Blended Crème',
            'iced_beverages': 'Cho tôi xem các loại Shaken Iced Beverages',
            'signature_espresso': 'Cho tôi xem các loại Signature Espresso Drinks',
            'smoothies': 'Cho tôi xem các loại Smoothies',
            'tea': 'Cho tôi xem các loại Tazo Tea Drinks'
        }
        return question_map.get(query_id, f"Cho tôi xem thông tin về {query_id}")

    def execute_query(self, query_id: str) -> Dict:
        """Execute a predefined query and return formatted results"""
        from utils import execute_sql_query

        if query_id not in self.predefined_queries:
            raise ValueError(f"Invalid query ID: {query_id}")

        query_info = self.predefined_queries[query_id]
        results = execute_sql_query(self.db_path, query_info['sql'])

        # Format results using the format function
        return query_info['format_function'](results)

    def format_items_for_chat_history(self, formatted_data: Dict) -> str:
        """Format items for chat history"""
        if formatted_data["type"] == "products":
            product_names = [item["name"] for item in formatted_data["items"]]
            product_list = ", ".join(product_names)
            return f"Đây là các sản phẩm trong danh mục {formatted_data['title']}: {product_list}"
        else:
            category_names = [item["name"] for item in formatted_data["items"]]
            category_list = ", ".join(category_names)
            return f"Đây là các danh mục đồ uống: {category_list}"

    def process_menu_suggestion(self, user_key: str, suggestion_type: str, category_id: Optional[str] = None) -> Dict:
        """Process menu suggestion request and return LLM-generated response"""
        from utils import get_all_categories, get_products_by_category, get_all_products
        from search_engine.get_URL_img import extract_product_images

        # Get data based on suggestion type
        if suggestion_type == 'category':
            # Get all categories for menu suggestions
            categories = get_all_categories(self.db_path)
            categories_text = "\n".join([f"{cat['name']}: {cat['description']}" for cat in categories])

            prompt = f"Dưới đây là danh sách các danh mục đồ uống. Hãy giới thiệu ngắn gọn về các danh mục này và gợi ý khách hàng nên chọn loại nào phù hợp với nhu cầu:\n\n{categories_text}"

        elif suggestion_type == 'product' and category_id:
            # Get products for a specific category
            products = get_products_by_category(self.db_path, category_id)
            category_name = products[0]['category'] if products else "không xác định"

            products_text = "\n".join([f"{prod['name']}: {prod['description']}" for prod in products])

            prompt = f"Dưới đây là danh sách các sản phẩm trong danh mục {category_name}. Hãy giới thiệu ngắn gọn về các sản phẩm này và gợi ý khách hàng nên chọn loại nào phù hợp với nhu cầu:\n\n{products_text}"
        else:
            # Get all products grouped by category
            all_products = get_all_products(self.db_path)

            # Group products by category
            products_by_category = {}
            for product in all_products:
                cat_name = product['category']
                if cat_name not in products_by_category:
                    products_by_category[cat_name] = []
                products_by_category[cat_name].append(product)

            # Format text for LLM
            products_text = ""
            for cat_name, products in products_by_category.items():
                products_text += f"\n== {cat_name} ==\n"
                products_text += "\n".join([f"{prod['name']}: {prod['description'][:100]}..." if len(prod['description']) > 100 else f"{prod['name']}: {prod['description']}" for prod in products])
                products_text += "\n"

            prompt = f"Dưới đây là danh sách các sản phẩm theo danh mục. Hãy giới thiệu ngắn gọn về các sản phẩm nổi bật và gợi ý khách hàng nên chọn loại nào phù hợp với nhu cầu:\n\n{products_text}"

        # Get response from LLM
        from system.rag_system import OptimizedRAGSystem
        rag_system = OptimizedRAGSystem(self.config)
        response = rag_system.answer_query(user_key, prompt)

        # Extract product images from the response
        product_images = extract_product_images(response, self.db_path)

        # Return response
        return {
            "role": "assistant",
            "content": response,
            "product_images": product_images
        }
