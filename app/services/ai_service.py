import logging
import json
import requests
import google.generativeai as genai
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        pass

    async def generate_response(
        self, 
        prompt: str, 
        provider: str, 
        api_key: str, 
        model_name: str = "gemini-pro", 
        system_prompt: Optional[str] = None,
        json_mode: bool = False
    ) -> str:
        """
        Generates a response from the specified AI provider.
        """
        if not api_key:
            raise ValueError(f"API Key for {provider} is missing.")

        try:
            if provider == "google":
                return await self._call_google(api_key, model_name, prompt, system_prompt, json_mode)
            elif provider == "openai":
                return await self._call_openai(api_key, model_name, prompt, system_prompt, json_mode)
            elif provider == "anthropic":
                return await self._call_anthropic(api_key, model_name, prompt, system_prompt)
            elif provider == "local":
                return await self._call_local(model_name, prompt, system_prompt)
            else:
                raise ValueError(f"Provider {provider} not supported.")
        except Exception as e:
            logger.error(f"AI Service Error ({provider}): {e}")
            raise e

    async def _call_google(self, api_key: str, model_name: str, prompt: str, system_prompt: str, json_mode: bool) -> str:
        genai.configure(api_key=api_key)
        
        # Gemini doesn't have a direct "system prompt" in the same way as OpenAI's chat, 
        # but we can prepend it or use specific config if available.
        # For simple generation:
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
            
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(full_prompt)
        
        text = response.text
        if json_mode:
            text = text.replace('```json', '').replace('```', '').strip()
            
        return text

    async def _call_openai(self, api_key: str, model_name: str, prompt: str, system_prompt: str, json_mode: bool) -> str:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Map model names if needed, or trust the caller
        model_to_use = model_name
        if "gpt-4" in model_name and "gpt-4" not in model_to_use:
             model_to_use = "gpt-4"
        elif "gpt-3.5" in model_name or not model_to_use:
             model_to_use = "gpt-3.5-turbo"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model_to_use,
            "messages": messages
        }
        
        if json_mode:
            # OpenAI supports json_object response format in newer models, but let's stick to prompt engineering + cleanup for broad compatibility
            # or add response_format={"type": "json_object"} if we are sure about the model version.
            # For now, we'll rely on the prompt asking for JSON and cleanup.
            pass

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            if json_mode:
                content = content.replace('```json', '').replace('```', '').strip()
            return content
        else:
            # Fallback logic could go here, but let's raise for now so the caller knows
            raise Exception(f"OpenAI API Error: {response.status_code} - {response.text}")

    async def _call_anthropic(self, api_key: str, model_name: str, prompt: str, system_prompt: str) -> str:
        # Placeholder for Anthropic
        return "Claude integration pending."

    async def _call_local(self, model_name: str, prompt: str, system_prompt: str) -> str:
        # Placeholder for Local LLM
        return "Local model integration pending."

ai_service = AIService()
