from typing import Dict, List, Optional
from config import Config

class SuggestionService:
    """Service class for handling menu suggestion operations"""

    def __init__(self, config: Config):
        self.config = config
        self.db_path = config.db_path
        self.category_map = self._initialize_category_map()
        self.predefined_queries = self._initialize_predefined_queries()

    def _initialize_category_map(self) -> Dict[str, str]:
        """Initialize mapping between query IDs and category names"""
        return {
            'classic_espresso': 'Classic Espresso Drinks',
            'coffee': 'Coffee',
            'frappuccino_coffee': 'Frappuccino Blended Coffee',
            'frappuccino_creme': 'Frappuccino Blended Crème',
            'iced_beverages': 'Shaken Iced Beverages',
            'signature_espresso': 'Signature Espresso Drinks',
            'smoothies': 'Smoothies',
            'tea': 'Tazo Tea Drinks'
        }

    def _initialize_predefined_queries(self) -> Dict:
        """Initialize predefined SQL queries for menu categories and products"""
        # Create a template for product queries
        def create_product_query(category_name):
            return {
                'sql': f"""
                    SELECT p.Id, p.Name_Product, p.Descriptions, c.Name_Cat
                    FROM Product p
                    JOIN Categories c ON p.Categories_id = c.Id
                    WHERE c.Name_Cat = '{category_name}'
                    ORDER BY p.Name_Product
                """,
                'format_function': lambda results: {
                    "type": "products",
                    "title": category_name,
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

        # Initialize the queries dictionary
        queries = {
            # Categories query
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
            }
        }

        # Add product queries using the template
        for query_id, category_name in self.category_map.items():
            queries[query_id] = create_product_query(category_name)

        return queries

    def get_question_for_query_id(self, query_id: str) -> str:
        """Get the corresponding question for a query ID"""
        if query_id == 'menu_categories':
            return 'Cho tôi xem danh mục đồ uống'
        elif query_id in self.category_map:
            return f'Cho tôi xem các loại {self.category_map[query_id]}'
        return f"Cho tôi xem thông tin về {query_id}"

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

    def process_menu_suggestion(self, user_key: str, rag_system, suggestion_type: str, category_id: Optional[str] = None) -> Dict:
        """Process menu suggestion request and return LLM-generated response"""
        from search_engine.get_URL_img import extract_product_images

        # Prepare prompt based on suggestion type
        prompt = self._prepare_suggestion_prompt(suggestion_type, category_id)

        # Get response from LLM using the provided RAG system instance
        response = rag_system.answer_query(user_key, prompt)

        # Extract product images from the response
        product_images = extract_product_images(response, self.db_path)

        # Return response
        return {
            "role": "assistant",
            "content": response,
            "product_images": product_images
        }

    def _prepare_suggestion_prompt(self, suggestion_type: str, category_id: Optional[str] = None) -> str:
        """Prepare prompt for menu suggestion based on type and category"""
        from utils import get_all_categories, get_products_by_category, get_all_products

        if suggestion_type == 'category':
            # Get all categories for menu suggestions
            categories = get_all_categories(self.db_path)
            categories_text = "\n".join([f"{cat['name']}: {cat['description']}" for cat in categories])
            return f"Dưới đây là danh sách các danh mục đồ uống. Hãy giới thiệu ngắn gọn về các danh mục này và gợi ý khách hàng nên chọn loại nào phù hợp với nhu cầu:\n\n{categories_text}"

        elif suggestion_type == 'product' and category_id:
            # Get products for a specific category
            products = get_products_by_category(self.db_path, category_id)
            category_name = products[0]['category'] if products else "không xác định"
            products_text = "\n".join([f"{prod['name']}: {prod['description']}" for prod in products])
            return f"Dưới đây là danh sách các sản phẩm trong danh mục {category_name}. Hãy giới thiệu ngắn gọn về các sản phẩm này và gợi ý khách hàng nên chọn loại nào phù hợp với nhu cầu:\n\n{products_text}"

        else:
            # Get all products and format by category
            all_products = get_all_products(self.db_path)
            products_text = self._format_all_products_text(all_products)
            return f"Dưới đây là danh sách các sản phẩm theo danh mục. Hãy giới thiệu ngắn gọn về các sản phẩm nổi bật và gợi ý khách hàng nên chọn loại nào phù hợp với nhu cầu:\n\n{products_text}"

    def _format_all_products_text(self, all_products: List[Dict]) -> str:
        """Format all products grouped by category for LLM prompt"""
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
            products_text += "\n".join([
                f"{prod['name']}: {prod['description'][:100]}..."
                if len(prod['description']) > 100
                else f"{prod['name']}: {prod['description']}"
                for prod in products
            ])
            products_text += "\n"

        return products_text
