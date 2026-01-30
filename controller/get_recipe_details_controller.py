import requests
import os
import json
from database.db import get_db_connection

def get_recipe_details_controller(user_id, data):
    menu_name = data.get('menu_name')
    cooking_time = data.get('cooking_time')
    
    if not menu_name or not cooking_time:
        return {"status": "error", "message": "menu_name and cooking_time are required."}, 400
    conn = get_db_connection()
    user_context = {}
    
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT ingredients, cuisine_preference, number_of_people FROM user_queries WHERE user_id = %s ORDER BY created_at DESC LIMIT 1"
            cursor.execute(query, (user_id,))
            record = cursor.fetchone()
            if record:
                user_context = {
                    "ingredients": json.loads(record['ingredients']),
                    "cuisine": record['cuisine_preference'],
                    "people": record['number_of_people']
                }
            cursor.close()
            conn.close()
        except Exception as db_err:
            print(f"Database Error: {str(db_err)}")

    if not user_context:
        return {"status": "error", "message": "No base data found. Please generate a recipe list first."}, 404

    user_items_str = ", ".join([f"{i['name']} ({i['qty']})" for i in user_context['ingredients']])

    prompt = f"""
    As a Professional Chef and Nutritionist, analyze the dish "{menu_name}" for {user_context['people']} people.
    Base Ingredients Available: {user_items_str}.
    Target Total Time: {cooking_time}.
    Cuisine: {user_context['cuisine']}.

    Tasks:
    1. Time: Split {cooking_time} into prep_time and cook_time. IMPORTANT: Always include 'min' after the cook_time value and prep_time value (e.g., "20 min").
    2. INGREDIENTS: Do NOT group items. List every single ingredient (like Salt, Cumin, Turmeric, Oil) as a separate object in the 'missing' or 'current' array. 
       - For 'missing' items, calculate exact quantities based on {user_items_str} items quantity and available {user_items_str}.
    3. Steps: Provide a comprehensive, numbered guide for both 'preparation' and 'cooking'. 
       - Preparation steps should include washing, cutting, and mixing instructions.
       - Cooking steps should include heat levels (low/medium/high) and visual cues (e.g., until golden brown).
       - Each step must be a separate detailed string in the array.
    4. NUTRITION: Provide ONLY exact numerical values with units (e.g., "320g", "2000 kcal"). 
       - Do NOT use the word "Approximately", "approx", or "based on...". 
       - Calculate based on scientific average values for the given quantities.
    5. SUITABILITY ANALYSIS: 
       - Calculate a dynamic scientific suitability percentage for Child, Adult, and Senior based on the nutritional content (Fat, Protein, Spice levels, and Digestibility) of the dish.
       - Do NOT use hardcoded values like 60%, 75%, 80%. 
       - Every dish must have unique percentages. For example, a spicy Biryani might have 40% for children but 85% for adults. 
       - Strictly follow this array structure: 
         "suitability": ["Child: [dynamic_value]%", "Adult: [dynamic_value]%", "Senior: [dynamic_value]%"]

    Response MUST be a clean JSON object:
    {{
      "menu_name": "{menu_name}",
      "servings": {user_context['people']},
      "time_breakdown": {{ "prep_time": "mins", "cook_time": "mins" }},
      "ingredients_analysis": {{
        "current": [{{"name": "string", "qty": "string"}}],
        "missing": [{{"name": "string", "qty": "string"}}]
      }},
      "suitability": ["string"],
      "steps": {{
        "preparation": ["1. Step one...", "2. Step two..."],
        "cooking": ["1. Step one...", "2. Step two..."]
      }},
      "nutrition": {{
        "total_calories": "kcal",
        "protein": "g",
        "fiber": "g",
        "fat": "g",
        "carbohydrates": "g"
      }}
    }}
    """

    api_url = os.getenv("MISTRAL_API_URL")
    model = os.getenv("MISTRAL_MODEL")

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": { "temperature": 0.1 } 
    }

    try:
        response = requests.post(api_url, json=payload, timeout=700)
        response.raise_for_status()
        result = response.json()
        
        raw_content = result.get('response')

        if not raw_content:
             return {"status": "error", "message": "AI returned an empty response."}, 500

        recipe_details = json.loads(raw_content.strip())
        
        return {
            "status": "success",
            "user_id": user_id,
            "details": recipe_details
        }, 200

    except Exception as e:
        return {"status": "error", "message": f"AI Analysis failed: {str(e)}"}, 500
    
def update_recipe_servings_controller(user_id, data):
    new_servings = data.get('new_servings')
    recipe_details = data.get('recipe_details') 

    if not new_servings or not recipe_details:
        return {"status": "error", "message": "new_servings and recipe_details are required."}, 400

    old_servings = recipe_details.get('servings', 1)
    scale_factor = float(new_servings) / float(old_servings)

    def scale_quantity(qty_str, factor):
        import re
        match = re.search(r"(\d+\.?\d*)\s*([a-zA-Z%]+)?", str(qty_str))
        if match:
            value = float(match.group(1)) * factor
            unit = match.group(2) if match.group(2) else ""
            formatted_value = int(value) if value.is_integer() else round(value, 2)
            return f"{formatted_value}{unit}"
        return qty_str

    try:
        recipe_details['servings'] = int(new_servings)

        for item in recipe_details.get('ingredients_analysis', {}).get('current', []):
            item['qty'] = scale_quantity(item['qty'], scale_factor)

        for item in recipe_details.get('ingredients_analysis', {}).get('missing', []):
            item['qty'] = scale_quantity(item['qty'], scale_factor)

        nutrition = recipe_details.get('nutrition', {})
        for key in ['total_calories', 'protein', 'fiber', 'fat', 'carbohydrates']:
            if key in nutrition:
                nutrition[key] = scale_quantity(nutrition[key], scale_factor)

        time_bd = recipe_details.get('time_breakdown', {})
        if 'prep_time' in time_bd:
            time_bd['prep_time'] = scale_quantity(time_bd['prep_time'], 1 + (scale_factor - 1) * 0.5)

        return {
            "status": "success",
            "message": f"Recipe scaled for {new_servings} servings successfully.",
            "details": recipe_details
        }, 200

    except Exception as e:
        return {"status": "error", "message": f"Scaling failed: {str(e)}"}, 500