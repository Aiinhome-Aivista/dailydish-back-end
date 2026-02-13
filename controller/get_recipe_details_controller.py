import requests
import os
import json
import re
from database.db import get_db_connection


def convert_to_grams(qty_str):
    """
    Convert various quantity formats to grams
    Returns: (grams, original_unit)
    """
    qty_str = str(qty_str).strip().lower()
    
    # Extract number and unit
    match = re.search(r'(\d+\.?\d*)\s*([a-zA-Z]+)?', qty_str)
    if not match:
        return 0, ''
    
    value = float(match.group(1))
    unit = match.group(2) if match.group(2) else ''
    
    # Conversion table
    conversions = {
        'g': 1,
        'kg': 1000,
        'ml': 1,  # Assuming 1ml = 1g for liquids
        'l': 1000,
        'tsp': 5,
        'tbsp': 15,
        'cup': 240,
        'piece': 150,  # Average piece weight
        'pieces': 150,
    }
    
    grams = value * conversions.get(unit, 1)
    return grams, unit


def get_nutrition_data_from_llm(ingredients_used):
    """
    Get per-100g nutrition data for each ingredient from LLM
    LLM ONLY provides the database values, NOT calculation
    Returns: dict mapping ingredient_name -> {calories, protein, fat, carbs, fiber} per 100g
    """
    ingredient_names = [ing.get('name', '') for ing in ingredients_used]
    
    prompt = f"""
You are a Nutrition Database Expert. Provide ONLY the nutritional values per 100g for each ingredient.

INGREDIENTS:
{json.dumps(ingredient_names, indent=2)}

YOUR TASK:
For EACH ingredient, provide scientifically accurate USDA/IFCT nutritional values PER 100g.

REFERENCE DATABASE (use these as guidelines):

PROTEINS (per 100g):
- Katla/Rohu/Fish: 120 kcal, 17.5g protein, 5.2g fat, 0g carbs, 0g fiber
- Chicken: 165 kcal, 31g protein, 3.6g fat, 0g carbs, 0g fiber
- Paneer: 265 kcal, 18.3g protein, 20.8g fat, 1.2g carbs, 0g fiber
- Egg: 155 kcal, 13g protein, 11g fat, 1.1g carbs, 0g fiber
- Mutton: 294 kcal, 25g protein, 21g fat, 0g carbs, 0g fiber
- Prawn/Shrimp: 99 kcal, 24g protein, 0.3g fat, 0.2g carbs, 0g fiber

VEGETABLES (per 100g):
- Potato: 77 kcal, 2g protein, 0.1g fat, 17g carbs, 2.2g fiber
- Tomato: 18 kcal, 0.9g protein, 0.2g fat, 3.9g carbs, 1.2g fiber
- Onion: 40 kcal, 1.1g protein, 0.1g fat, 9.3g carbs, 1.7g fiber
- Cauliflower: 25 kcal, 1.9g protein, 0.3g fat, 5g carbs, 2g fiber
- Broccoli: 34 kcal, 2.8g protein, 0.4g fat, 7g carbs, 2.6g fiber
- Capsicum/Bell Pepper: 20 kcal, 0.9g protein, 0.2g fat, 4.6g carbs, 1.7g fiber
- Mushroom: 22 kcal, 3.1g protein, 0.3g fat, 3.3g carbs, 1g fiber
- Carrot: 41 kcal, 0.9g protein, 0.2g fat, 10g carbs, 2.8g fiber
- Spinach: 23 kcal, 2.9g protein, 0.4g fat, 3.6g carbs, 2.2g fiber
- Cabbage: 25 kcal, 1.3g protein, 0.1g fat, 6g carbs, 2.5g fiber

GRAINS (per 100g):
- Rice (cooked): 130 kcal, 2.7g protein, 0.3g fat, 28g carbs, 0.4g fiber
- Pasta (cooked): 131 kcal, 5g protein, 1.1g fat, 25g carbs, 1.8g fiber
- Wheat Flour: 364 kcal, 10.7g protein, 1.7g fat, 76g carbs, 2.7g fiber
- Bread: 265 kcal, 9g protein, 3.2g fat, 49g carbs, 2.7g fiber

OILS & FATS (per 100g):
- Oil (any): 884 kcal, 0g protein, 100g fat, 0g carbs, 0g fiber
- Butter: 717 kcal, 0.9g protein, 81g fat, 0.1g carbs, 0g fiber
- Ghee: 900 kcal, 0g protein, 100g fat, 0g carbs, 0g fiber

DAIRY (per 100g):
- Milk: 61 kcal, 3.2g protein, 3.3g fat, 4.8g carbs, 0g fiber
- Yogurt: 59 kcal, 3.5g protein, 0.4g fat, 4.7g carbs, 0g fiber
- Cheese: 402 kcal, 25g protein, 33g fat, 1.3g carbs, 0g fiber

SPICES (per 100g - typically used in very small amounts):
- Salt: 0 kcal, 0g protein, 0g fat, 0g carbs, 0g fiber
- Turmeric: 312 kcal, 10g protein, 3.2g fat, 67g carbs, 22.7g fiber
- Cumin: 375 kcal, 18g protein, 22g fat, 44g carbs, 11g fiber
- Chili Powder: 282 kcal, 13g protein, 15g fat, 50g carbs, 28g fiber
- Coriander: 23 kcal, 2.1g protein, 0.5g fat, 3.7g carbs, 2.8g fiber
- Ginger: 80 kcal, 1.8g protein, 0.8g fat, 18g carbs, 2g fiber
- Garlic: 149 kcal, 6.4g protein, 0.5g fat, 33g carbs, 2.1g fiber

LEGUMES (per 100g):
- Chickpeas: 164 kcal, 9g protein, 2.6g fat, 27g carbs, 7.6g fiber
- Lentils: 116 kcal, 9g protein, 0.4g fat, 20g carbs, 7.9g fiber
- Kidney Beans: 127 kcal, 8.7g protein, 0.5g fat, 23g carbs, 6.4g fiber

NUTS (per 100g):
- Almonds: 579 kcal, 21g protein, 50g fat, 22g carbs, 12g fiber
- Cashews: 553 kcal, 18g protein, 44g fat, 30g carbs, 3.3g fiber
- Peanuts: 567 kcal, 26g protein, 49g fat, 16g carbs, 8.5g fiber

FRUITS (per 100g):
- Apple: 52 kcal, 0.3g protein, 0.2g fat, 14g carbs, 2.4g fiber
- Banana: 89 kcal, 1.1g protein, 0.3g fat, 23g carbs, 2.6g fiber
- Orange: 47 kcal, 0.9g protein, 0.1g fat, 12g carbs, 2.4g fiber

CRITICAL INSTRUCTIONS:
1. Return ONLY the per-100g values for each ingredient
2. DO NOT calculate total nutrition
3. Use closest match from database
4. Return in strict JSON format

RESPONSE FORMAT (strict JSON):
{{
  "Katla Fish": {{"calories": 120, "protein": 17.5, "fat": 5.2, "carbs": 0, "fiber": 0}},
  "Salt": {{"calories": 0, "protein": 0, "fat": 0, "carbs": 0, "fiber": 0}},
  "Oil": {{"calories": 884, "protein": 0, "fat": 100, "carbs": 0, "fiber": 0}}
}}

Return ONLY the JSON object mapping each ingredient to its per-100g nutrition data.
"""

    api_url = os.getenv("MISTRAL_API_URL")
    model = os.getenv("MISTRAL_MODEL")

    if not api_url or not model:
        raise Exception("MISTRAL_API_URL or MISTRAL_MODEL environment variables not set")

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1}
    }

    max_retries = 3
    last_error = None
    
    for attempt in range(max_retries):
        try:
            print(f"Fetching nutrition database from LLM, attempt {attempt + 1}/{max_retries}...")
            response = requests.post(api_url, json=payload, timeout=700)
            response.raise_for_status()
            result = response.json()
            
            raw_content = result.get('response', '').strip()
            
            if not raw_content:
                raise Exception("Empty response from LLM")
            
            # Clean up response
            if raw_content.startswith('```json'):
                raw_content = raw_content.replace('```json', '').replace('```', '').strip()
            elif raw_content.startswith('```'):
                raw_content = raw_content.replace('```', '').strip()
            
            nutrition_db = json.loads(raw_content)
            
            # Validate that we got data for all ingredients
            for ing_name in ingredient_names:
                if ing_name not in nutrition_db:
                    raise Exception(f"Missing nutrition data for: {ing_name}")
                
                # Validate structure
                required_keys = ['calories', 'protein', 'fat', 'carbs', 'fiber']
                for key in required_keys:
                    if key not in nutrition_db[ing_name]:
                        raise Exception(f"Missing '{key}' for {ing_name}")
            
            print(f"Nutrition database fetched successfully")
            return nutrition_db
            
        except json.JSONDecodeError as je:
            last_error = f"JSON parsing error: {str(je)}"
            print(f"Attempt {attempt + 1} failed: {last_error}")
            if attempt < max_retries - 1:
                continue
        except Exception as e:
            last_error = str(e)
            print(f"Attempt {attempt + 1} failed: {last_error}")
            if attempt < max_retries - 1:
                continue
    
    raise Exception(f"Failed to fetch nutrition database after {max_retries} attempts. Last error: {last_error}")


def calculate_nutrition_python(ingredients_used):
    """
    Calculate total nutrition using PYTHON with scientific logic
    Step 1: Get per-100g data from LLM (database lookup only)
    Step 2: Python does the mathematical calculation
    Returns: dict with total nutrition values
    """
    # Step 1: Get nutrition database from LLM (NO calculation, just data)
    print("Step 1: Fetching per-100g nutrition data from LLM...")
    nutrition_db = get_nutrition_data_from_llm(ingredients_used)
    
    # Step 2: Python calculates total nutrition scientifically
    print("Step 2: Python calculating total nutrition scientifically...")
    total_nutrition = {
        'calories': 0.0,
        'protein': 0.0,
        'fat': 0.0,
        'carbs': 0.0,
        'fiber': 0.0
    }
    
    for ingredient in ingredients_used:
        name = ingredient.get('name', '')
        model_qty = ingredient.get('model_qty', '0')
        
        # Convert to grams
        grams, _ = convert_to_grams(model_qty)
        
        # Get per-100g nutrition data
        if name not in nutrition_db:
            print(f"Warning: {name} not found in nutrition database, skipping")
            continue
        
        per_100g = nutrition_db[name]
        
        # Python Scientific Calculation: (grams / 100) × per_100g_value
        multiplier = grams / 100.0
        
        total_nutrition['calories'] += per_100g['calories'] * multiplier
        total_nutrition['protein'] += per_100g['protein'] * multiplier
        total_nutrition['fat'] += per_100g['fat'] * multiplier
        total_nutrition['carbs'] += per_100g['carbs'] * multiplier
        total_nutrition['fiber'] += per_100g['fiber'] * multiplier
        
        print(f"  {name} ({grams}g): {per_100g['calories'] * multiplier:.1f} kcal")
    
    # Format output
    formatted_nutrition = {
        'total_calories': f"{round(total_nutrition['calories'], 1)} kcal",
        'protein': f"{round(total_nutrition['protein'], 1)} g",
        'fat': f"{round(total_nutrition['fat'], 1)} g",
        'carbohydrates': f"{round(total_nutrition['carbs'], 1)} g",
        'fiber': f"{round(total_nutrition['fiber'], 1)} g"
    }
    
    print(f"Total Nutrition (Python calculated): {formatted_nutrition}")
    return formatted_nutrition


def extract_unit_from_qty(qty_str):
    """
    Extract unit from quantity string
    Returns: unit (e.g., 'pieces', 'g', 'kg', etc.)
    """
    qty_str = str(qty_str).strip().lower()
    match = re.search(r'(\d+\.?\d*)\s*([a-zA-Z]+)?', qty_str)
    if match and match.group(2):
        return match.group(2)
    return ''


def get_llm_suitability_analysis(nutrition_data, dish_info, servings):
    """
    LLM-based suitability analysis with detailed reasoning
    Returns comprehensive analysis for child, adult, and senior suitability
    """
    # Extract numerical values from nutrition data
    def extract_number(value_str):
        import re
        match = re.search(r'(\d+\.?\d*)', str(value_str))
        return float(match.group(1)) if match else 0
    
    total_calories = extract_number(nutrition_data.get('total_calories', '0'))
    total_protein = extract_number(nutrition_data.get('protein', '0'))
    total_fat = extract_number(nutrition_data.get('fat', '0'))
    total_fiber = extract_number(nutrition_data.get('fiber', '0'))
    total_carbs = extract_number(nutrition_data.get('carbohydrates', '0'))
    
    menu_name = dish_info.get('menu_name', '')
    
    # Calculate per-serving values for better analysis
    per_serving_calories = total_calories / servings if servings > 0 else total_calories
    per_serving_protein = total_protein / servings if servings > 0 else total_protein
    per_serving_fat = total_fat / servings if servings > 0 else total_fat
    per_serving_fiber = total_fiber / servings if servings > 0 else total_fiber
    per_serving_carbs = total_carbs / servings if servings > 0 else total_carbs
    
    prompt = f"""
You are a Nutritionist Expert analyzing dish suitability for different age groups.

DISH ANALYSIS:
- Dish Name: {menu_name}
- Total Servings: {servings} people

NUTRITIONAL VALUES:
Per Serving (for 1 person):
- Calories: {per_serving_calories:.1f} kcal
- Protein: {per_serving_protein:.1f} g
- Fat: {per_serving_fat:.1f} g
- Fiber: {per_serving_fiber:.1f} g
- Carbohydrates: {per_serving_carbs:.1f} g

Total (for all {servings} servings):
- Total Calories: {total_calories} kcal
- Total Protein: {total_protein} g
- Total Fat: {total_fat} g
- Total Fiber: {total_fiber} g
- Total Carbohydrates: {total_carbs} g

YOUR TASK:
Analyze this dish's suitability for three age groups: Child (5-12 years), Adult (18-60 years), and Senior (60+ years).

For EACH age group, provide:

1. SUITABILITY PERCENTAGE (20-95%):
   - Calculate based on PER SERVING nutritional values
   - Use the per-serving values provided above
   
2. POSITIVE FACTORS (why it's good):
   - List 1-3 specific nutritional benefits
   - Reference exact per-serving values
   - Show percentage contribution (e.g., "adds +8%", "adds +10%")
   
3. NEGATIVE FACTORS (why it's concerning):
   - List 2-5 specific nutritional concerns
   - Reference exact per-serving values
   - Show percentage reduction (e.g., "reduces -15%", "reduces -20%")
   
4. FINAL RECOMMENDATION:
   - Clear verdict: "Highly Recommended" / "Recommended with Moderation" / "Not Recommended"
   - One-line reasoning explaining why

NUTRITIONAL REFERENCE RANGES (per serving):

CHILD (5-12 years):
- Calories: 300-500 kcal (ideal), <250 or >600 problematic
- Protein: 10-20g (ideal), <8g or >25g problematic
- Fat: 10-20g (ideal), <8g or >30g problematic
- Fiber: 3-5g (good), 0-2g (poor)
- Avoid: Very spicy, very high fat/sodium

ADULT (18-60 years):
- Calories: 400-700 kcal (ideal), <300 or >850 problematic
- Protein: 15-30g (ideal), <12g or >45g concerning
- Fat: 15-30g (ideal), <10g or >40g problematic
- Fiber: 5-10g (good), 0-3g (poor)

SENIOR (60+ years):
- Calories: 300-550 kcal (ideal), <250 or >650 problematic
- Protein: 20-30g (ideal for muscle), <15g or >35g concerning
- Fat: 10-20g (ideal), <8g or >25g problematic
- Fiber: 5-8g (important), 0-3g (poor for digestion)
- Avoid: Heavy/fried, excessive fat, high sodium

CALCULATION METHODOLOGY:
1. Start with base: 100%
2. Add positive %: Each benefit adds +3% to +10%
3. Subtract negative %: Each concern reduces -5% to -25%
4. Formula: Final = 100% + (sum of positive) + (sum of negative)
5. Clamp between 20-95%
6. SHOW YOUR MATH in the calculation field!

RESPONSE FORMAT (strict JSON, NO extra text):
{{
  "child": {{
    "suitability_percentage": 63,
    "positive_factors": [
      "Good protein content ({per_serving_protein:.1f}g per serving) supports growth (adds +8%)"
    ],
    "negative_factors": [
      "Very high fat content ({per_serving_fat:.1f}g per serving) exceeds safe limit for children (reduces -22%)",
      "High calories ({per_serving_calories:.1f} kcal) exceeds recommended range (reduces -15%)",
      "Zero fiber content ({per_serving_fiber:.1f}g) impacts digestion (reduces -8%)"
    ],
    "calculation": "Base: 100% | Positive: +8% | Negative: -22% -15% -8% = -45% | Final: 100% + 8% - 45% = 63%",
    "recommendation": "Not Recommended - Too high in fat and calories for children's needs and digestive capacity."
  }},
  "adult": {{
    "suitability_percentage": 72,
    "positive_factors": [
      "Excellent protein ({per_serving_protein:.1f}g) supports muscle maintenance (adds +10%)",
      "High energy density suitable for active adults (adds +7%)"
    ],
    "negative_factors": [
      "Very high fat ({per_serving_fat:.1f}g) exceeds daily limit (reduces -15%)",
      "High caloric load requires active lifestyle (reduces -10%)",
      "No fiber impacts digestive health (reduces -5%)"
    ],
    "calculation": "Base: 100% | Positive: +10% +7% = +17% | Negative: -15% -10% -5% = -30% | Final: 100% + 17% - 30% = 87% → adjusted to 72%",
    "recommendation": "Recommended with Moderation - Good for active adults but pair with fiber-rich vegetables."
  }},
  "senior": {{
    "suitability_percentage": 48,
    "positive_factors": [
      "Good protein ({per_serving_protein:.1f}g) helps maintain muscle mass (adds +9%)"
    ],
    "negative_factors": [
      "Excessive fat ({per_serving_fat:.1f}g) hard to digest for seniors (reduces -20%)",
      "High calories ({per_serving_calories:.1f} kcal) may strain metabolism (reduces -15%)",
      "Zero fiber severely impacts digestive health (reduces -12%)",
      "Heavy meal may cause discomfort and bloating (reduces -7%)"
    ],
    "calculation": "Base: 100% | Positive: +9% | Negative: -20% -15% -12% -7% = -54% | Final: 100% + 9% - 54% = 55% → adjusted to 48%",
    "recommendation": "Not Recommended - Too fatty and heavy for senior digestive systems, high indigestion risk."
  }}
}}

CRITICAL RULES:
- Use ONLY per-serving values in your analysis
- Reference the exact numbers I provided
- Show complete math in calculation field
- Make suitability_percentage match your calculation
- Return ONLY valid JSON, no markdown or extra text
- Be realistic and scientific in scoring
"""

    api_url = os.getenv("MISTRAL_API_URL")
    model = os.getenv("MISTRAL_MODEL")

    if not api_url or not model:
        raise Exception("MISTRAL_API_URL or MISTRAL_MODEL environment variables not set")

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.2}
    }

    # Retry logic with 3 attempts
    max_retries = 3
    last_error = None
    
    for attempt in range(max_retries):
        try:
            print(f"Suitability analysis attempt {attempt + 1}/{max_retries}...")
            response = requests.post(api_url, json=payload, timeout=700)
            response.raise_for_status()
            result = response.json()
            
            raw_content = result.get('response', '').strip()
            
            if not raw_content:
                raise Exception("Empty response from LLM")
            
            # Clean up response - remove markdown code blocks if present
            if raw_content.startswith('```json'):
                raw_content = raw_content.replace('```json', '').replace('```', '').strip()
            elif raw_content.startswith('```'):
                raw_content = raw_content.replace('```', '').strip()
            
            suitability_data = json.loads(raw_content)
            
            # Validate response structure
            required_keys = ['child', 'adult', 'senior']
            for key in required_keys:
                if key not in suitability_data:
                    raise Exception(f"Missing '{key}' in suitability response")
                
                age_group = suitability_data[key]
                if 'suitability_percentage' not in age_group:
                    raise Exception(f"Missing 'suitability_percentage' for {key}")
                if 'positive_factors' not in age_group:
                    raise Exception(f"Missing 'positive_factors' for {key}")
                if 'negative_factors' not in age_group:
                    raise Exception(f"Missing 'negative_factors' for {key}")
                if 'recommendation' not in age_group:
                    raise Exception(f"Missing 'recommendation' for {key}")
            
            print(f"Suitability analysis successful on attempt {attempt + 1}")
            return suitability_data
            
        except json.JSONDecodeError as je:
            last_error = f"JSON parsing error: {str(je)}"
            print(f"Attempt {attempt + 1} failed: {last_error}")
            if attempt < max_retries - 1:
                continue
        except requests.exceptions.Timeout:
            last_error = "Request timeout - LLM took too long to respond"
            print(f"Attempt {attempt + 1} failed: {last_error}")
            if attempt < max_retries - 1:
                continue
        except requests.exceptions.RequestException as re:
            last_error = f"Request error: {str(re)}"
            print(f"Attempt {attempt + 1} failed: {last_error}")
            if attempt < max_retries - 1:
                continue
        except Exception as e:
            last_error = str(e)
            print(f"Attempt {attempt + 1} failed: {last_error}")
            if attempt < max_retries - 1:
                continue
    
    # If all retries failed, raise the error instead of returning fallback
    raise Exception(f"Suitability analysis failed after {max_retries} attempts. Last error: {last_error}")


def format_suitability_output(suitability_data):
    """
    Format LLM suitability data into API response format
    """
    return {
        "suitability": [
            f"Child: {suitability_data['child']['suitability_percentage']}%",
            f"Adult: {suitability_data['adult']['suitability_percentage']}%",
            f"Senior: {suitability_data['senior']['suitability_percentage']}%"
        ],
        "suitability_reasons": {
            "child": suitability_data['child']['positive_factors'] + suitability_data['child']['negative_factors'] + [suitability_data['child']['recommendation']],
            "adult": suitability_data['adult']['positive_factors'] + suitability_data['adult']['negative_factors'] + [suitability_data['adult']['recommendation']],
            "senior": suitability_data['senior']['positive_factors'] + suitability_data['senior']['negative_factors'] + [suitability_data['senior']['recommendation']]
        }
    }


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
            "available_qty": ingredient['qty'],
            "unit": extract_unit_from_qty(ingredient['qty'])  # Extract unit
        })
    
    # Create readable string for prompt
    ingredients_str = ", ".join([f"{i['name']} ({i['available_qty']})" for i in ingredients_list])

    prompt = f"""
You are a Professional Chef. Create a recipe for "{menu_name}" for {user_context['people']} people.

CRITICAL RESTRICTION - VIOLATION = REJECTION:
You can ONLY use these {len(ingredients_list)} ingredients. NO additions, NO substitutions, NO exceptions:
{ingredients_str}

If you add ANY ingredient not in this list, the recipe will be REJECTED.

Available Ingredients List with Units:
{json.dumps(ingredients_list, indent=2)}

Recipe Details:
- Target Time: {cooking_time}
- Cuisine: {user_context['cuisine']}
- Servings: {user_context['people']} people

YOUR TASKS:

1. TIME BREAKDOWN:
   Split {cooking_time} into prep_time and cook_time
   - Format: "X min" (example: "20 min", "30 min")
   - CRITICAL: prep_time + cook_time MUST EQUAL {cooking_time}
   - Example: If total is "45 min", then prep_time: "10 min" + cook_time: "35 min" = 45 min

2. INGREDIENTS CALCULATION WITH UNIT MATCHING:
   For EACH of the {len(ingredients_list)} ingredients:
   - Calculate the IDEAL/REQUIRED quantity for a PROPER meal for {user_context['people']} people
   - model_qty = What the recipe SHOULD have for good portion sizes
   - **CRITICAL: Use the SAME UNIT as the user provided**
   
   UNIT MATCHING RULES:
   - If user provided "2 pieces", you MUST suggest in "pieces" (e.g., "4 pieces")
   - If user provided "100g", you MUST suggest in "g" (e.g., "250g")
   - If user provided "1 kg", you MUST suggest in "kg" (e.g., "1.5 kg")
   - If user provided "2 tsp", you MUST suggest in "tsp" (e.g., "3 tsp")
   
   Return format: {{"name": "ingredient_name", "model_qty": "ideal_quantity_with_same_unit"}}
   
   PROPER PORTION GUIDELINES (per person):
   - Main protein (Paneer/Chicken/Fish): 80-120g per person OR 1-2 pieces per person
   - Vegetables: 100-150g per person OR 1-2 pieces per person
   - Mushrooms: 50-80g per person
   - Rice/Flour: 80-100g per person
   - Spices: 1-2 tsp total for entire dish
   - Oil: 1-2 tbsp total for cooking
   
   REALISTIC CALCULATION EXAMPLES for {user_context['people']} people:
   - User gave "Mushroom: 100g" → model_qty should be in grams: {{"name": "Mushroom", "model_qty": "200g"}}
   - User gave "Paneer: 2 pieces" → model_qty should be in pieces: {{"name": "Paneer", "model_qty": "4 pieces"}}
   - User gave "Fish: 3 pieces" → model_qty should be in pieces: {{"name": "Fish", "model_qty": "6 pieces"}}
   - User gave "Oil: 50g" → model_qty should be in grams: {{"name": "Oil", "model_qty": "150g"}}
   - User gave "Salt: 1 tsp" → model_qty should be in tsp: {{"name": "Salt", "model_qty": "2 tsp"}}
   
   IMPORTANT: 
   - Calculate based on PROPER serving sizes, not available quantity
   - **ALWAYS match the unit type (pieces → pieces, g → g, kg → kg, tsp → tsp)**
   - This helps user understand if they have enough ingredients
   - model_qty shows the IDEAL amount needed in the SAME UNIT FORMAT
   
   Include ALL {len(ingredients_list)} ingredients with proper model_qty calculations in matching units.

3. COOKING STEPS - NATURAL LANGUAGE TIME FORMAT:
   
   PREPARATION STEPS:
   - Write each step in natural, conversational language
   - Include time WITHIN the sentence naturally
   - Format: "Step description (takes about X minutes)" or "Step for X minutes on medium heat"
   - Examples:
     * "Wash and clean the Katla fish thoroughly, which should take about 5 minutes, then pat dry with paper towels"
     * "Season the fish generously with salt on both sides, allowing it to rest for 3 minutes to absorb the flavors"
     * "Chop the vegetables finely for approximately 4 minutes"
   
   COOKING STEPS:
   - Write each step with heat level and timing embedded naturally
   - Include visual cues and techniques
   - Format: "Cook description for X minutes on [heat level]" or "Description (X minutes, [heat level])"
   - Examples:
     * "Heat the oil in a grill pan over medium-high heat for about 2 minutes until it starts shimmering"
     * "Place the fish on the grill and cook for 5 minutes on each side over medium heat until golden brown and crispy"
     * "Let the fish rest for 3 minutes on low heat before serving to retain juices"
     * "Sauté the vegetables for 7-8 minutes on medium-high heat, stirring occasionally until tender"
   
   CRITICAL RULES:
   - NO parentheses with just time like "(5 min, medium heat)" - integrate into sentence
   - NO numbered formats like "1 (5 min): Do this" - write naturally
   - Times should flow naturally in the description
   - Always mention heat level (low/medium/medium-high/high) for cooking steps
   - Use approximate language: "about", "for approximately", "takes around"
   - Reference the ingredients and model_qty in your steps
   - Use ONLY ingredients from the available list
   
   TOTAL TIME VALIDATION:
   - Sum of all preparation step times should approximately match prep_time
   - Sum of all cooking step times should approximately match cook_time

RESPONSE FORMAT (strict JSON):
{{
  "menu_name": "{menu_name}",
  "servings": {user_context['people']},
  "time_breakdown": {{
    "prep_time": "X min",
    "cook_time": "Y min"
  }},
  "ingredients_used": [
    {{"name": "Katla Fish", "model_qty": "4 pieces"}},
    {{"name": "Salt", "model_qty": "2 tsp"}},
    {{"name": "Oil", "model_qty": "150g"}},
    ... (all {len(ingredients_list)} ingredients with MATCHING UNITS)
  ],
  "steps": {{
    "preparation": [
      "Wash and clean the Katla fish thoroughly, which should take about 5 minutes, then pat dry with paper towels",
      "Season the fish generously with salt on both sides, allowing it to rest for 3 minutes to absorb the flavors"
    ],
    "cooking": [
      "Heat the oil in a grill pan over medium-high heat for about 2 minutes until it starts shimmering",
      "Place the fish on the grill and cook for 5 minutes on each side over medium heat until golden brown and crispy",
      "Let the fish rest for 3 minutes on low heat before serving to retain the juices"
    ]
  }}
}}

**DO NOT INCLUDE nutrition field in response - it will be calculated separately by Python**

FINAL VERIFICATION:
- Count ingredients_used array length = {len(ingredients_list)} ✓
- Every ingredient name matches the available list ✓
- NO extra ingredients added ✓
- model_qty uses SAME UNIT TYPE as user's qty ✓
- model_qty is TOTAL for {user_context['people']} people ✓
- prep_time + cook_time = {cooking_time} ✓
- Steps written in natural language with embedded times ✓
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
                    "name": matched_user_ing['name'],
                    "qty": matched_user_ing['qty'],
                    "model_qty": ai_ing.get('model_qty')
                })
        
        recipe_details['ingredients_used'] = final_ingredients
        
        # CALCULATE NUTRITION USING PYTHON (Scientific Method)
        print("=" * 60)
        print("NUTRITION CALCULATION - PYTHON SCIENTIFIC METHOD")
        print("=" * 60)
        nutrition_data = calculate_nutrition_python(recipe_details['ingredients_used'])
        recipe_details['nutrition'] = nutrition_data
        print("=" * 60)
        
        # Get LLM-based suitability analysis with error handling
        try:
            suitability_analysis = get_llm_suitability_analysis(
                nutrition_data,
                {
                    'menu_name': menu_name,
                    'servings': user_context['people']
                },
                user_context['people']
            )
            
            # Format suitability data for response
            suitability_formatted = format_suitability_output(suitability_analysis)
            
            # Add suitability data to recipe details
            recipe_details['suitability'] = suitability_formatted['suitability']
            recipe_details['suitability_reasons'] = suitability_formatted['suitability_reasons']
            
        except Exception as suit_err:
            print(f"Suitability analysis error: {str(suit_err)}")
            # Provide basic suitability without detailed analysis
            recipe_details['suitability'] = [
                "Child: 70%",
                "Adult: 80%",
                "Senior: 65%"
            ]
            recipe_details['suitability_reasons'] = {
                "child": [
                    "Nutritional suitability analysis is temporarily unavailable. Please consult the nutrition values to assess appropriateness for children."
                ],
                "adult": [
                    "Nutritional suitability analysis is temporarily unavailable. Please review the nutrition values provided."
                ],
                "senior": [
                    "Nutritional suitability analysis is temporarily unavailable. Please consult a nutritionist for personalized dietary advice."
                ]
            }
        
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
            # Keep decimal precision for scaled values
            formatted_value = round(value, 1) if not value.is_integer() else int(value)
            return f"{formatted_value}{unit}" if unit else f"{formatted_value}"
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

        # RECALCULATE NUTRITION USING PYTHON (with scaled ingredients)
        print("=" * 60)
        print(f"RECALCULATING NUTRITION FOR {new_servings} SERVINGS")
        print("=" * 60)
        nutrition_data = calculate_nutrition_python(recipe_details['ingredients_used'])
        recipe_details['nutrition'] = nutrition_data
        print("=" * 60)

        # Update time (prep time scales slightly with servings)
        time_bd = recipe_details.get('time_breakdown', {})
        if 'prep_time' in time_bd:
            time_bd['prep_time'] = scale_quantity(time_bd['prep_time'], 1 + (scale_factor - 1) * 0.5)

        # Steps remain UNCHANGED (as requested)
        
        # Recalculate suitability with new nutrition values using LLM
        try:
            suitability_analysis = get_llm_suitability_analysis(
                nutrition_data,
                {
                    'menu_name': recipe_details.get('menu_name', ''),
                    'servings': int(new_servings)
                },
                int(new_servings)
            )
            
            # Format suitability data for response
            suitability_formatted = format_suitability_output(suitability_analysis)
            
            # Update suitability data in recipe details
            recipe_details['suitability'] = suitability_formatted['suitability']
            recipe_details['suitability_reasons'] = suitability_formatted['suitability_reasons']
            
        except Exception as suit_err:
            print(f"Suitability recalculation error: {str(suit_err)}")
            # Keep existing suitability or provide basic values
            if 'suitability' not in recipe_details:
                recipe_details['suitability'] = [
                    "Child: 70%",
                    "Adult: 80%",
                    "Senior: 65%"
                ]
            if 'suitability_reasons' not in recipe_details:
                recipe_details['suitability_reasons'] = {
                    "child": ["Suitability analysis temporarily unavailable"],
                    "adult": ["Suitability analysis temporarily unavailable"],
                    "senior": ["Suitability analysis temporarily unavailable"]
                }

        return {
            "status": "success",
            "message": f"Recipe scaled for {new_servings} servings successfully.",
            "details": recipe_details
        }, 200

    except Exception as e:
        return {"status": "error", "message": f"Scaling failed: {str(e)}"}, 500