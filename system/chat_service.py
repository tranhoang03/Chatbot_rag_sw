from typing import Dict, List, Any, Optional
from flask import session
from system.rag_system import OptimizedRAGSystem
from system.menu_service import MenuService
from search_engine.get_URL_img import extract_product_images

class ChatService:
    """Service class for handling chat-related operations"""

    def __init__(self, rag_system: OptimizedRAGSystem, menu_service: MenuService):
        self.rag_system = rag_system
        self.menu_service = menu_service

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
        formatted_data = self.menu_service.execute_query(query_id)

        # Get question for query ID
        user_question = self.menu_service.get_question_for_query_id(query_id)

        # Format items for chat history
        assistant_response = self.menu_service.format_items_for_chat_history(formatted_data)

        # Add to chat history
        try:
            self.rag_system.chat_history.add_chat(user_key, user_question, assistant_response)
            print(f"Added suggested query to chat history for user: {user_key}")
        except Exception as e:
            print(f"Error adding suggested query to chat history: {e}")

        # Get product images
        product_images = []
        if formatted_data["type"] == "products":
            for item in formatted_data["items"]:
                product_name = item["name"]
                image_info = extract_product_images(product_name, self.menu_service.db_path)
                if image_info:
                    product_images.extend(image_info)

        # Return response
        return {
            "role": "assistant",
            "content_type": "menu_data",
            "data": formatted_data,
            "product_images": product_images
        }

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
            product_images = extract_product_images(response, self.menu_service.db_path)

            # Return response
            return {
                "role": "assistant",
                "content": response,
                "product_images": product_images
            }
        except Exception as e:
            print(f"Error getting RAG response: {e}")

            try:
                self.rag_system.chat_history.add_chat(user_key, user_query, f"ERROR: {e}")
            except Exception as hist_e:
                print(f"Failed to add error to chat history: {hist_e}")

            return {"error": "Failed to get response from assistant"}, 500

    def process_menu_suggestion(self, suggestion_type: str, category_id: Optional[str] = None) -> Dict:
        """Process menu suggestion request and return LLM-generated response"""
        # Ensure valid session
        self.ensure_valid_session()

        # Get user key
        user_key = self.get_user_key_from_session()

        # Process menu suggestion using MenuService
        return self.menu_service.process_menu_suggestion(user_key, suggestion_type, category_id)
