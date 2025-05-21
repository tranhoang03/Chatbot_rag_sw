from typing import Dict, List, Optional
from flask import session
from system.rag_system import OptimizedRAGSystem
from services.suggestion_service import SuggestionService

class SuggestionQueryHandler:
    """Handler class for processing suggestion queries"""

    def __init__(self, rag_system: OptimizedRAGSystem, suggestion_service: SuggestionService):
        self.rag_system = rag_system
        self.suggestion_service = suggestion_service

    def get_user_key_from_session(self) -> str:
        """Get user key from session"""
        user_key = "anonymous"
        if session.get('authenticated', False):
            auth_user_info = session.get('user_info')
            if auth_user_info and 'id' in auth_user_info:
                user_key = str(auth_user_info['id'])
        return user_key

    def ensure_valid_session(self):
        """Ensure session is valid, set to anonymous if needed"""
        if not session.get('authenticated', False) and not session.get('anonymous', False):
            print("WARNING: No valid session state found. Setting to anonymous.")
            session['anonymous'] = True

    def process_suggested_query(self, query_id: str) -> Dict:
        """Process a suggested query and add to chat history"""
        # Ensure valid session
        self.ensure_valid_session()

        # Get user key
        user_key = self.get_user_key_from_session()

        # Execute query
        formatted_data = self.suggestion_service.execute_query(query_id)

        # Get question for query ID and add to chat history
        user_question = self.suggestion_service.get_question_for_query_id(query_id)
        assistant_response = self.suggestion_service.format_items_for_chat_history(formatted_data)

        # Add to chat history in a single try-except block
        self._add_to_chat_history(user_key, user_question, assistant_response)

        # Get product images if this is a product query
        product_images = self._get_product_images_for_query(formatted_data)

        # Return response
        return {
            "role": "assistant",
            "content_type": "menu_data",
            "data": formatted_data,
            "product_images": product_images
        }

    def _add_to_chat_history(self, user_key: str, user_question: str, assistant_response: str) -> None:
        """Add a conversation to chat history with error handling"""
        try:
            self.rag_system.chat_history.add_chat(user_key, user_question, assistant_response)
            print(f"Added to chat history for user: {user_key}")
        except Exception as e:
            print(f"Error adding to chat history: {e}")

    def _get_product_images_for_query(self, formatted_data: Dict) -> List:
        """Get product images for query results"""
        from search_engine.get_URL_img import extract_product_images

        product_images = []
        if formatted_data["type"] == "products":
            for item in formatted_data["items"]:
                product_name = item["name"]
                image_info = extract_product_images(product_name, self.suggestion_service.db_path)
                if image_info:
                    product_images.extend(image_info)

        return product_images

    def process_chat_message(self, user_query: str) -> Dict:
        """Process a chat message and return response"""
        # Ensure valid session
        self.ensure_valid_session()

        # Get user key
        user_key = self.get_user_key_from_session()

        try:
            # Get response from RAG system
            response = self.rag_system.answer_query(user_key, user_query)

            # Extract product images from the response
            from search_engine.get_URL_img import extract_product_images
            product_images = extract_product_images(response, self.suggestion_service.db_path)

            # Return response
            return {
                "role": "assistant",
                "content": response,
                "product_images": product_images
            }
        except Exception as e:
            print(f"Error getting RAG response: {e}")

            # Add error to chat history
            self._add_to_chat_history(user_key, user_query, f"ERROR: {e}")

            return {"error": "Failed to get response from assistant"}, 500

    def process_menu_suggestion(self, suggestion_type: str, category_id: Optional[str] = None) -> Dict:
        """Process menu suggestion request and return LLM-generated response"""
        # Ensure valid session
        self.ensure_valid_session()

        # Get user key
        user_key = self.get_user_key_from_session()

        # Process menu suggestion using SuggestionService, passing the existing RAG system instance
        return self.suggestion_service.process_menu_suggestion(user_key, self.rag_system, suggestion_type, category_id)
