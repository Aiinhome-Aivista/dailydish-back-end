import requests
import os
import json

def get_cuisine_common_items_controller(user_id, data):
    cuisine = data.get('cuisine')

    if not cuisine:
        return {"status": "error", "message": "Cuisine name is required."}, 400

    prompt = f"""
    As a Culinary Expert, list all the common spices, herbs, and essential cooking items (like oils, salts, etc.) 
    that are fundamental to {cuisine} cuisine. These should be items that are used in almost every dish of this cuisine.

    Response MUST be a clean JSON object with the following structure:
    {{
      "cuisine": "{cuisine}",
      "common_spices": ["Spice 1", "Spice 2", "Spice 3"],
      "essential_cooking_items": ["Item 1", "Item 2", "Item 3"],
      "description": "A brief sentence about the flavor profile of this cuisine."
    }}
    
    Ensure the list is comprehensive and specific to {cuisine}.
    """

    api_url = os.getenv("MISTRAL_API_URL")
    model = os.getenv("MISTRAL_MODEL")

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": { "temperature": 0.3 } 
    }

    try:
        response = requests.post(api_url, json=payload, timeout=700)
        response.raise_for_status()
        result = response.json()
        
        raw_content = result.get('response')

        if not raw_content:
             return {"status": "error", "message": "AI returned an empty response."}, 500

        common_items = json.loads(raw_content.strip())
        
        return {
            "status": "success",
            "user_id": user_id,
            "data": common_items
        }, 200

    except Exception as e:
        return {"status": "error", "message": f"LLM Processing failed: {str(e)}"}, 500