import requests
import os
import json
from database.db import get_db_connection

def calculate_suitability(nutrition_data, dish_info):
    """
    Scientific suitability calculation based on nutritional content
    Returns: {"child": percentage, "adult": percentage, "senior": percentage}
    """
    try:
        # Extract numerical values from nutrition data
        def extract_number(value_str):
            import re
            match = re.search(r'(\d+\.?\d*)', str(value_str))
            return float(match.group(1)) if match else 0
        
        calories = extract_number(nutrition_data.get('total_calories', '0'))
        protein = extract_number(nutrition_data.get('protein', '0'))
        fat = extract_number(nutrition_data.get('fat', '0'))
        fiber = extract_number(nutrition_data.get('fiber', '0'))
        carbs = extract_number(nutrition_data.get('carbohydrates', '0'))
        
        servings = dish_info.get('servings', 1)
        per_serving_calories = calories / servings if servings > 0 else calories
        per_serving_fat = fat / servings if servings > 0 else fat
        per_serving_protein = protein / servings if servings > 0 else protein
        
        # Child Suitability (Age 5-12)
        child_score = 100
        
        if per_serving_calories > 600:
            child_score -= 20
        elif per_serving_calories > 500:
            child_score -= 10
        elif per_serving_calories < 250:
            child_score -= 15
            
        if per_serving_fat > 20:
            child_score -= 25
        elif per_serving_fat > 15:
            child_score -= 10
            
        if per_serving_protein < 8:
            child_score -= 10
        elif per_serving_protein > 20:
            child_score -= 5
            
        dish_name_lower = dish_info.get('menu_name', '').lower()
        spicy_keywords = ['spicy', 'chili', 'hot', 'vindaloo', 'madras', 'jalfrezi']
        if any(keyword in dish_name_lower for keyword in spicy_keywords):
            child_score -= 20
            
        child_suitability = max(30, min(95, child_score))
        
        # Adult Suitability (Age 18-60)
        adult_score = 100
        
        if per_serving_calories > 800:
            adult_score -= 10
        elif per_serving_calories < 300:
            adult_score -= 10
            
        if per_serving_protein < 10:
            adult_score -= 15
        elif per_serving_protein > 40:
            adult_score -= 5
            
        if per_serving_fat > 30:
            adult_score -= 10
        elif per_serving_fat < 5:
            adult_score -= 5
            
        adult_suitability = max(60, min(95, adult_score))
        
        # Senior Suitability (Age 60+)
        senior_score = 100
        
        if per_serving_calories > 600:
            senior_score -= 15
        elif per_serving_calories > 500:
            senior_score -= 8
        elif per_serving_calories < 300:
            senior_score -= 10
            
        if per_serving_fat > 18:
            senior_score -= 20
        elif per_serving_fat > 12:
            senior_score -= 10
            
        if fiber < 3:
            senior_score -= 10
        elif fiber > 8:
            senior_score += 5
            
        if per_serving_protein < 12:
            senior_score -= 12
        elif per_serving_protein > 25:
            senior_score -= 8
            
        if any(keyword in dish_name_lower for keyword in spicy_keywords):
            senior_score -= 25
            
        if per_serving_fat > 20:
            senior_score -= 10
            
        senior_suitability = max(35, min(90, senior_score))
        
        return {
            "child": int(child_suitability),
            "adult": int(adult_suitability),
            "senior": int(senior_suitability)
        }
        
    except Exception as e:
        print(f"Suitability calculation error: {str(e)}")
        return {"child": 65, "adult": 80, "senior": 70}


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

    # Create ingredient list for prompt
    ingredients_list = []
    for ingredient in user_context['ingredients']:
        ingredients_list.append({
            "name": ingredient['name'],
            "available_qty": ingredient['qty']
        })
    
    # Create readable string for prompt
    ingredients_str = ", ".join([f"{i['name']} ({i['available_qty']})" for i in ingredients_list])

    prompt = f"""
You are a Professional Chef. Create a recipe for "{menu_name}" for {user_context['people']} people.

 CRITICAL RESTRICTION - VIOLATION = REJECTION:
You can ONLY use these {len(ingredients_list)} ingredients. NO additions, NO substitutions, NO exceptions:
{ingredients_str}

If you add ANY ingredient not in this list, the recipe will be REJECTED.

Available Ingredients List:
{json.dumps(ingredients_list, indent=2)}

Recipe Details:
- Target Time: {cooking_time}
- Cuisine: {user_context['cuisine']}
- Servings: {user_context['people']} people

YOUR TASKS:

1. TIME BREAKDOWN:
   Split {cooking_time} into prep_time and cook_time
   - Format: "X min" (example: "20 min", "30 min")

2. INGREDIENTS CALCULATION:
   For EACH of the {len(ingredients_list)} ingredients:
   - Calculate the IDEAL/REQUIRED quantity for a PROPER meal for {user_context['people']} people
   - model_qty = What the recipe SHOULD have for good portion sizes
   - DON'T limit yourself to available quantity - calculate what's actually needed!
   
   Return format: {{"name": "ingredient_name", "model_qty": "ideal_quantity_needed"}}
   
   PROPER PORTION GUIDELINES (per person):
   - Main protein (Paneer/Chicken/Fish): 80-120g per person
   - Vegetables: 100-150g per person  
   - Mushrooms: 50-80g per person
   - Rice/Flour: 80-100g per person
   - Spices: 1-2 tsp total for entire dish
   - Oil: 1-2 tbsp total for cooking
   
   REALISTIC CALCULATION EXAMPLES for {user_context['people']} people:
    Mushroom (50g per person × 2) = {{"name": "Mushroom", "model_qty": "100g"}}
    Paneer (100g per person × 3) = {{"name": "Paneer", "model_qty": "300g"}}
    Broccoli (120g per person × 2) = {{"name": "Broccoli", "model_qty": "240g"}}
    Cumin (for whole dish) = {{"name": "Cumin", "model_qty": "1.5 tsp"}}
   
   IMPORTANT: 
   - Calculate based on PROPER serving sizes, not available quantity
   - This helps user understand if they have enough ingredients
   - model_qty shows the IDEAL amount needed
   
    Include ALL {len(ingredients_list)} ingredients with proper model_qty calculations.

3. COOKING STEPS:
   - Preparation steps: washing, cutting, mixing (separate detailed steps)
   - Cooking steps: heat levels, cooking time, visual cues
   - Reference the ingredients and model_qty in your steps
   - Use ONLY ingredients from the available list

4. NUTRITION CALCULATION:
   Calculate TOTAL nutrition for ALL {user_context['people']} servings combined
   - Based on the model_qty you calculated
   - Format: "exact_value unit" (e.g., "2000 kcal", "45 g")
   - NO approximations or ranges

RESPONSE FORMAT (strict JSON):
{{
  "menu_name": "{menu_name}",
  "servings": {user_context['people']},
  "time_breakdown": {{
    "prep_time": "X min",
    "cook_time": "Y min"
  }},
  "ingredients_used": [
    {{"name": "Paneer", "model_qty": "150g"}},
    {{"name": "Broccoli", "model_qty": "1 piece"}},
    ... (all {len(ingredients_list)} ingredients)
  ],
  "steps": {{
    "preparation": ["1. First prep step", "2. Second prep step"],
    "cooking": ["1. First cooking step", "2. Second cooking step"]
  }},
  "nutrition": {{
    "total_calories": "X kcal",
    "protein": "X g",
    "fiber": "X g",
    "fat": "X g",
    "carbohydrates": "X g"
  }}
}}

 FINAL VERIFICATION:
- Count ingredients_used array length = {len(ingredients_list)} ✓
- Every ingredient name matches the available list ✓
- NO extra ingredients added ✓
- model_qty is TOTAL for {user_context['people']} people ✓
    """

    api_url = os.getenv("MISTRAL_API_URL")
    model = os.getenv("MISTRAL_MODEL")

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1}
    }

    try:
        response = requests.post(api_url, json=payload, timeout=700)
        response.raise_for_status()
        result = response.json()
        
        raw_content = result.get('response')

        if not raw_content:
            return {"status": "error", "message": "AI returned an empty response."}, 500

        recipe_details = json.loads(raw_content.strip())
        
        # STRICT VALIDATION: Check for extra ingredients
        user_ingredient_names = {ing['name'].lower() for ing in user_context['ingredients']}
        ai_ingredient_names = {ing.get('name', '').lower() for ing in recipe_details.get('ingredients_used', [])}
        
        extra_ingredients = ai_ingredient_names - user_ingredient_names
        if extra_ingredients:
            return {
                "status": "error", 
                "message": f"AI added unauthorized ingredients: {', '.join(extra_ingredients)}. Only use user's ingredients."
            }, 500
        
        # Validate model_qty exists for all ingredients
        for ai_ing in recipe_details.get('ingredients_used', []):
            if 'model_qty' not in ai_ing:
                return {
                    "status": "error",
                    "message": f"Missing model_qty for ingredient: {ai_ing.get('name')}"
                }, 500
        
        # Add user's original qty + keep AI's model_qty
        # qty = What user has available (from database, never changes)
        # model_qty = What recipe actually needs (calculated by AI, scales with servings)
        user_ingredients_map = {ing['name'].lower(): ing for ing in user_context['ingredients']}
        
        final_ingredients = []
        for ai_ing in recipe_details.get('ingredients_used', []):
            ing_name_lower = ai_ing.get('name', '').lower()
            
            # Find matching user ingredient
            matched_user_ing = None
            for user_key, user_val in user_ingredients_map.items():
                if user_key == ing_name_lower:
                    matched_user_ing = user_val
                    break
            
            if matched_user_ing:
                final_ingredients.append({
                    "name": matched_user_ing['name'],      # Original user name
                    "qty": matched_user_ing['qty'],        # What user HAS (never changes)
                    "model_qty": ai_ing.get('model_qty')   # What recipe NEEDS (scales with servings)
                })
        
        recipe_details['ingredients_used'] = final_ingredients
        
        # Calculate suitability
        suitability_scores = calculate_suitability(
            recipe_details.get('nutrition', {}),
            {
                'menu_name': menu_name,
                'servings': user_context['people']
            }
        )
        
        recipe_details['suitability'] = [
            f"Child: {suitability_scores['child']}%",
            f"Adult: {suitability_scores['adult']}%",
            f"Senior: {suitability_scores['senior']}%"
        ]
        
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
        # Update servings count
        recipe_details['servings'] = int(new_servings)

        # Update ingredients: qty stays same, model_qty scales
        for item in recipe_details.get('ingredients_used', []):
            # qty remains unchanged (user's original)
            # Only scale model_qty
            if 'model_qty' in item:
                item['model_qty'] = scale_quantity(item['model_qty'], scale_factor)

        # Update nutrition values (total values scale with servings)
        nutrition = recipe_details.get('nutrition', {})
        for key in ['total_calories', 'protein', 'fiber', 'fat', 'carbohydrates']:
            if key in nutrition:
                nutrition[key] = scale_quantity(nutrition[key], scale_factor)

        # Update time (prep time scales slightly with servings)
        time_bd = recipe_details.get('time_breakdown', {})
        if 'prep_time' in time_bd:
            time_bd['prep_time'] = scale_quantity(time_bd['prep_time'], 1 + (scale_factor - 1) * 0.5)

        # Steps remain UNCHANGED (as requested)
        
        # Recalculate suitability with new nutrition values
        suitability_scores = calculate_suitability(
            nutrition,
            {
                'menu_name': recipe_details.get('menu_name', ''),
                'servings': int(new_servings)
            }
        )
        
        recipe_details['suitability'] = [
            f"Child: {suitability_scores['child']}%",
            f"Adult: {suitability_scores['adult']}%",
            f"Senior: {suitability_scores['senior']}%"
        ]

        return {
            "status": "success",
            "message": f"Recipe scaled for {new_servings} servings successfully.",
            "details": recipe_details
        }, 200

    except Exception as e:
        return {"status": "error", "message": f"Scaling failed: {str(e)}"}, 500