"""
LLM utility functions for dynamic model client creation.
Supports OpenAI, Anthropic, and Google Gemini models.
API keys loaded from environment variables or .env file.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class LLMClient:
    """
    Dynamic LLM client that automatically detects model provider and creates appropriate client.
    """
    
    def __init__(self):
        """
        Initialize LLM client with API keys from environment variables.
        """
        self.clients = {}
        
        # Get API keys from environment variables
        self.api_keys = {
            'openai': os.getenv('OPENAI_API_KEY'),
            'anthropic': os.getenv('ANTHROPIC_API_KEY'),
            'google': os.getenv('GEMINI_API_KEY')
        }
    
    def _detect_provider(self, model: str) -> str:
        """
        Detect the provider based on model name.
        
        Args:
            model (str): Model name
            
        Returns:
            str: Provider name ('openai', 'anthropic', 'google')
        """
        model = model.lower()
        
        # OpenAI models (text and vision)
        openai_models = [
            'o4-mini', # 4r, 3s, $1.10 (ip), $0.28 (cachee), $4.40 (op) 
            'gpt-4.1-mini', # 3i, 4s, $0.40 (ip), $0.1 (cachee), $1.60 (op) 
            'gpt-4.1-nano', # 2i, 5s, $0.10 (ip), $0.03 (cachee), $0.40 (op) 
            'gpt-4.1', # 4i, 3s, $2.00 (ip), $0.50 (cachee), $8.00 (op) 
            'gpt-4o-mini',  # 2i, 4s, $0.15 (ip), $0.08 (cachee), $0.60 (op) 
            'gpt-4o', # 3i, 3s, $2.50 (ip), $1.25 (cachee), $10.00 (op) 
            'o3' # 5r, 1s, $2.00 (ip), $0.50 (cachee), $8.00 (op) 
        ]
        
        # Anthropic models (text and vision)
        anthropic_models = [
            'claude-opus-4-0',
            'claude-sonnet-4-0', 
            'claude-3-7-sonnet-latest',
            'claude-3-5-sonnet-latest',
            'claude-3-5-haiku-latest',
            'claude-3-haiku'
        ]
        
        # Google models (text and vision)
        google_models = [
            'gemini-2.5-pro',
            'gemini-2.5-flash',
            'gemini-2.0-flash',
            'gemini-2.0-flash-lite'
        ]
        
        # Direct model name matching
        if model in openai_models:
            return 'openai'
        elif model in anthropic_models:
            return 'anthropic'
        elif model in google_models:
            return 'google'
        
        raise ValueError(f"Unsupported model: {model}. Supported models:\n"
                        f"OpenAI: {', '.join(openai_models)}\n"
                        f"Anthropic: {', '.join(anthropic_models)}\n"
                        f"Google: {', '.join(google_models)}")
    
    def _create_openai_client(self):
        """Create OpenAI client."""
        try:
            import openai
            if not self.api_keys.get('openai'):
                raise ValueError("OpenAI API key not provided")
            
            client = openai.OpenAI(api_key=self.api_keys['openai'])
            return client
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: pip install openai")
    
    def _create_anthropic_client(self):
        """Create Anthropic client."""
        try:
            import anthropic
            if not self.api_keys.get('anthropic'):
                raise ValueError("Anthropic API key not provided")
            
            client = anthropic.Anthropic(api_key=self.api_keys['anthropic'])
            return client
        except ImportError:
            raise ImportError("Anthropic package not installed. Run: pip install anthropic")
    
    def _create_google_client(self):
        """Create Google Generative AI client."""
        try:
            from google import genai
            if not self.api_keys.get('google'):
                raise ValueError("Google API key not provided")
            
            client = genai.Client(api_key=self.api_keys['google'])
            return client
        except ImportError:
            raise ImportError("Google Generative AI package not installed. Run: pip install google-genai")
    
    def get_client(self, model: str):
        """
        Get or create client for the specified model.
        
        Args:
            model (str): Model name
            
        Returns:
            tuple: (client_object, provider_name)
        """
        provider = self._detect_provider(model)
        
        if provider not in self.clients:
            if provider == 'openai':
                self.clients[provider] = self._create_openai_client()
            elif provider == 'anthropic':
                self.clients[provider] = self._create_anthropic_client()
            elif provider == 'google':
                self.clients[provider] = self._create_google_client()
        
        return self.clients[provider], provider
        
    def format_messages(self, model: str, system_prompt: Optional[str] = None, user_prompt: str = "", image_data: Optional[bytes] = None, image_mime_type: Optional[str] = None):
        """
        Format messages for the specific provider based on model.
        
        Args:
            model (str): Model name
            system_prompt (str, optional): System instruction/prompt
            user_prompt (str): User message content
            image_data (bytes, optional): Image data as bytes
            image_mime_type (str, optional): MIME type of image (e.g., 'image/jpeg', 'image/png')
            
        Returns:
            dict: Formatted messages/content for the specific provider
        """
        provider = self._detect_provider(model)
        
        if provider == 'openai':
            return self._format_openai_messages(system_prompt, user_prompt, image_data, image_mime_type)
        elif provider == 'anthropic':
            return self._format_anthropic_messages(system_prompt, user_prompt, image_data, image_mime_type)
        elif provider == 'google':
            return self._format_google_messages(system_prompt, user_prompt, image_data, image_mime_type)
    
    def _format_openai_messages(self, system_prompt: Optional[str], user_prompt: str, image_data: Optional[bytes], image_mime_type: Optional[str]):
        """Format messages for OpenAI."""
        messages = []
        
        # Add system message if provided
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Create user message content
        user_content = []
        
        # Add text content
        if user_prompt:
            user_content.append({
                "type": "text",
                "text": user_prompt
            })
        
        # Add image content if provided
        if image_data and image_mime_type:
            import base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{image_mime_type};base64,{image_base64}"
                }
            })
        
        messages.append({
            "role": "user",
            "content": user_content if len(user_content) > 1 else user_prompt
        })
        
        return {"messages": messages}
    
    def _format_anthropic_messages(self, system_prompt: Optional[str], user_prompt: str, image_data: Optional[bytes], image_mime_type: Optional[str]):
        """Format messages for Anthropic."""
        # Anthropic separates system prompt from messages
        messages = []
        
        # Create user message content
        user_content = []
        
        # Add text content
        if user_prompt:
            user_content.append({
                "type": "text",
                "text": user_prompt
            })
        
        # Add image content if provided
        if image_data and image_mime_type:
            import base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            user_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image_mime_type,
                    "data": image_base64
                }
            })
        
        messages.append({
            "role": "user",
            "content": user_content
        })
        
        result = {"messages": messages}
        if system_prompt:
            result["system"] = system_prompt
            
        return result
    
    def query(self, model: str, system_prompt: Optional[str] = None, user_prompt: str = "", image_data: Optional[bytes] = None, image_mime_type: Optional[str] = None, **kwargs):
        """
        Query the model with formatted messages.
        
        Args:
            model (str): Model name
            system_prompt (str, optional): System instruction/prompt
            user_prompt (str): User message content
            image_data (bytes, optional): Image data as bytes
            image_mime_type (str, optional): MIME type of image
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            dict: Standardized response with 'content', 'usage', 'model', 'provider' keys
        """
        client, provider = self.get_client(model)
        formatted_data = self.format_messages(model, system_prompt, user_prompt, image_data, image_mime_type)
        
        try:
            if provider == 'openai':
                return self._query_openai(client, model, formatted_data, **kwargs)
            elif provider == 'anthropic':
                return self._query_anthropic(client, model, formatted_data, **kwargs)
            elif provider == 'google':
                return self._query_google(client, model, formatted_data, **kwargs)
        except Exception as e:
            raise Exception(f"Error querying {provider} with model {model}: {str(e)}")
    
    def _query_openai(self, client, model: str, formatted_data: dict, **kwargs):
        """Query OpenAI API."""
        response = client.chat.completions.create(
            model=model,
            messages=formatted_data["messages"],
            **kwargs
        )
        
        return {
            'content': response.choices[0].message.content,
            'usage': {
                'prompt_tokens': response.usage.prompt_tokens if response.usage else 0,
                'completion_tokens': response.usage.completion_tokens if response.usage else 0,
                'total_tokens': response.usage.total_tokens if response.usage else 0
            },
            'model': response.model,
            'provider': 'openai'
        }
    
    def _query_anthropic(self, client, model: str, formatted_data: dict, **kwargs):
        """Query Anthropic API."""
        # Separate system prompt from messages for Anthropic
        request_params = {
            'model': model,
            'messages': formatted_data["messages"],
            **kwargs
        }
        
        # Add system prompt if present
        if "system" in formatted_data:
            request_params['system'] = formatted_data["system"]
        
        response = client.messages.create(**request_params)
        
        return {
            'content': response.content[0].text,
            'usage': {
                'prompt_tokens': response.usage.input_tokens if hasattr(response, 'usage') else 0,
                'completion_tokens': response.usage.output_tokens if hasattr(response, 'usage') else 0,
                'total_tokens': (response.usage.input_tokens + response.usage.output_tokens) if hasattr(response, 'usage') else 0
            },
            'model': response.model,
            'provider': 'anthropic'
        }
    
    def _query_google(self, client, model: str, formatted_data: dict, **kwargs):
        """Query Google API."""
        from google.genai import types
        
        # Map common parameters to Google's parameter names
        google_kwargs = {}
        if 'max_tokens' in kwargs:
            google_kwargs['max_output_tokens'] = kwargs['max_tokens']
        if 'temperature' in kwargs:
            google_kwargs['temperature'] = kwargs['temperature']
        if 'top_p' in kwargs:
            google_kwargs['top_p'] = kwargs['top_p']
        if 'top_k' in kwargs:
            google_kwargs['top_k'] = kwargs['top_k']
        
        # Get existing config or create new one
        config = formatted_data.get("config")
        
        if config:
            # Update existing config with mapped parameters
            for key, value in google_kwargs.items():
                setattr(config, key, value)
        elif google_kwargs:
            # Create new config with mapped parameters
            config = types.GenerateContentConfig(**google_kwargs)
        
        request_params = {
            'model': model,
            'contents': formatted_data["contents"]
        }
        
        if config:
            request_params['config'] = config
        
        response = client.models.generate_content(**request_params)
        
        return {
            'content': response.text,
            'usage': {
                'prompt_tokens': response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0,
                'completion_tokens': response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0,
                'total_tokens': response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0
            },
            'model': model,
            'provider': 'google'
        }
    
    def _format_google_messages(self, system_prompt: Optional[str], user_prompt: str, image_data: Optional[bytes], image_mime_type: Optional[str]):
        """Format messages for Google."""
        from google.genai import types
        
        # Create parts list
        parts = []
        
        # Add text part
        if user_prompt:
            parts.append(types.Part.from_text(text=user_prompt))
        
        # Add image part if provided
        if image_data and image_mime_type:
            parts.append(types.Part.from_bytes(data=image_data, mime_type=image_mime_type))
        
        # Create content
        contents = [types.Content(role='user', parts=parts)]
        
        result = {"contents": contents}
        
        # Add system instruction if provided
        if system_prompt:
            result["config"] = types.GenerateContentConfig(
                system_instruction=system_prompt
            )
            
        return result


# Convenience function for quick usage
def create_llm_client() -> LLMClient:
    """
    Create and return an LLM client with API keys from environment variables.
        
    Returns:
        LLMClient: Initialized LLM client
    """
    return LLMClient()


# Example usage and testing
if __name__ == "__main__":
    # Example usage
    client = create_llm_client()
    
    # Test model detection
    test_models = [
        "o4-mini",
        "gpt-4.1-mini", 
        "gpt-4o",
        "claude-sonnet-4-0",
        "claude-3-5-haiku-latest",
        "gemini-2.5-pro",
        "gemini-2.0-flash"
    ]
    
    print("Model Provider Detection:")
    for model in test_models:
        try:
            provider = client._detect_provider(model)
            print(f"  {model:<25} -> {provider}")
        except ValueError as e:
            print(f"  {model:<25} -> ERROR: {e}")
    
    # Example client creation and query
    try:
        llm = create_llm_client()
        
        # Test text-only query
        response = llm.query(
            model="gpt-4o",
            system_prompt="You are a helpful assistant",
            user_prompt="What is 2+2?",
            temperature=0.7,
            max_tokens=100
        )
        
        print(f"\nResponse from {response['provider']}:")
        print(f"Content: {response['content']}")
        print(f"Usage: {response['usage']}")
        
    except Exception as e:
        print(f"Error: {e}")
        
    # Example with image (commented out - add your image data)
    """
    try:
        with open("image.jpg", "rb") as f:
            image_data = f.read()
            
        response = llm.query(
            model="claude-sonnet-4-0",
            system_prompt="Analyze this image carefully",
            user_prompt="What do you see?",
            image_data=image_data,
            image_mime_type="image/jpeg",
            temperature=0.5
        )
        
        print(f"Image analysis: {response['content']}")
        
    except Exception as e:
        print(f"Error with image: {e}")
    """