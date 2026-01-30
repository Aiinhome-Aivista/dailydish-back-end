import datetime
import hashlib
import random
import requests
import os
import json
from functools import lru_cache
from database.db import get_db_connection 

# ============================================================================
# INGREDIENT VALIDATOR CLASS - ENHANCED WITH MORE FOODS
# ============================================================================
class IngredientValidator:
    """
    Production-ready ingredient validator using USDA FoodData Central API
    - Fixed API endpoint and parameters
    - Strict validation
    - Performance caching
    - EXPANDED fallback list with Bengali/Asian ingredients
    """
    
    def __init__(self):
        self.usda_key = os.getenv("USDA_API_KEY")
        self.cache = {}
        
        # Condiment keywords
        self.condiment_keywords = [
            'spices', 'seasonings', 'salt', 'oil', 'condiments', 
            'sauces', 'vinegar', 'pepper', 'herbs', 'baking'
        ]
        
        # EXPANDED fallback list - includes Bengali/Asian ingredients
        self.common_foods = {
            # Proteins
            'chicken', 'rice', 'fish', 'beef', 'pork', 'lamb', 'egg', 'shrimp',
            'salmon', 'tuna', 'prawns', 'crab', 'lobster', 'duck', 'turkey',
            
            # Bengali/Asian Fish
            'katla', 'rui', 'rohu', 'hilsa', 'ilish', 'pomfret', 'bhetki',
            'magur', 'tengra', 'pabda', 'chingri', 'bagda',
            
            # Vegetables
            'potato', 'tomato', 'onion', 'garlic', 'carrot', 'beans', 'lentils',
            'spinach', 'cabbage', 'broccoli', 'mushroom', 'corn', 'peas',
            'cauliflower', 'eggplant', 'brinjal', 'okra', 'cucumber', 'lettuce',
            'bell pepper', 'capsicum', 'ginger', 'chili', 'celery', 'radish',
            'turnip', 'beetroot', 'pumpkin', 'zucchini', 'squash', 'kale',
            
            # Bengali/Asian Vegetables
            'begun', 'lau', 'kumro', 'potol', 'jhinge', 'dharosh', 'sheem',
            'barbati', 'data', 'chichinga', 'uchche', 'korola',
            
            # Dairy
            'milk', 'cheese', 'butter', 'yogurt', 'cream', 'paneer', 'panner',
            'curd', 'ghee', 'tofu',
            
            # Grains & Staples
            'pasta', 'noodles', 'bread', 'flour', 'sugar', 'dal', 'moong',
            'masoor', 'chana', 'toor', 'urad', 'chickpeas',
            
            # Fruits
            'apple', 'banana', 'orange', 'mango', 'pineapple', 'grapes',
            'strawberry', 'watermelon', 'papaya', 'lemon', 'lime',
            
            # Meat variants
            'mutton', 'goat', 'venison', 'quail'
        }
        
        # EXPANDED condiments - includes spices with underscores/hyphens
        self.common_condiments = {
            # Basic
            'salt', 'pepper', 'oil', 'vinegar', 'water', 'soy sauce',
            
            # Oils
            'olive oil', 'vegetable oil', 'sesame oil', 'mustard oil',
            'coconut oil', 'sunflower oil', 'canola oil',
            
            # Spices (with variants)
            'black pepper', 'black_pepper', 'white pepper', 'white_pepper',
            'red pepper', 'red_pepper', 'cayenne', 'cayenne_pepper',
            'turmeric', 'cumin', 'coriander', 'cardamom', 'cinnamon',
            'clove', 'cloves', 'bay leaf', 'bay_leaf', 'star anise', 'star_anise',
            'fennel', 'fenugreek', 'mustard seeds', 'mustard_seeds',
            'curry leaves', 'curry_leaves', 'dried chili', 'dried_chili',
            
            # Garam masala components
            'garam masala', 'garam_masala', 'chaat masala', 'chaat_masala',
            'tandoori masala', 'tandoori_masala', 'biryani masala', 'biryani_masala',
            
            # Herbs
            'basil', 'parsley', 'mint', 'coriander leaves', 'cilantro',
            'thyme', 'rosemary', 'oregano', 'dill', 'sage',
            
            # Sauces & Pastes
            'tomato paste', 'tomato_paste', 'ginger paste', 'ginger_paste',
            'garlic paste', 'garlic_paste', 'chili sauce', 'chili_sauce',
            'oyster sauce', 'oyster_sauce', 'fish sauce', 'fish_sauce',
            'hoisin sauce', 'hoisin_sauce', 'sriracha', 'ketchup', 'mayo',
            
            # Other
            'sugar', 'honey', 'jaggery', 'tamarind', 'coconut milk', 'coconut_milk'
        }
    
    @lru_cache(maxsize=1000)
    def is_valid_ingredient(self, ingredient_name):
        """Validate ingredient"""
        ingredient_name = ingredient_name.strip().lower()
        
        # Normalize underscores/hyphens to spaces for matching
        normalized_name = ingredient_name.replace('_', ' ').replace('-', ' ')
        
        # Cache check
        if ingredient_name in self.cache:
            return self.cache[ingredient_name]
        
        # Empty check
        if not ingredient_name or len(ingredient_name) < 2:
            return {"valid": False, "is_condiment": False, "source": "pre-check"}
        
        # Try USDA API
        if self.usda_key:
            result = self._check_usda(normalized_name)
            if result['checked']:
                self.cache[ingredient_name] = result
                return result
        
        # Fallback to common foods (strict mode)
        print(f"  Using fallback validation for: {ingredient_name}")
        result = self._check_common_foods(normalized_name)
        self.cache[ingredient_name] = result
        return result
    
    def _check_usda(self, ingredient_name):
        """
        Check USDA API - FIXED version
        API Docs: https://fdc.nal.usda.gov/api-guide.html
        """
        try:
            # CORRECT USDA API endpoint
            url = "https://api.nal.usda.gov/fdc/v1/foods/search"
            
            # Simplified params
            params = {
                "query": ingredient_name,
                "pageSize": 5,
                "api_key": self.usda_key
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            # Debug info
            print(f" USDA API Status: {response.status_code} for '{ingredient_name}'")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('foods') and len(data['foods']) > 0:
                    # Check for good matches
                    for food in data['foods']:
                        food_desc = food.get('description', '').lower()
                        
                        # Fuzzy matching
                        if (ingredient_name in food_desc or 
                            food_desc.startswith(ingredient_name[:3]) or
                            self._similarity_check(ingredient_name, food_desc)):
                            
                            category = food.get('foodCategory', '').lower()
                            is_condiment = any(kw in category for kw in self.condiment_keywords)
                            
                            print(f" USDA Match: '{ingredient_name}' → '{food_desc}'")
                            return {
                                "valid": True,
                                "is_condiment": is_condiment,
                                "matched_name": food_desc,
                                "category": category,
                                "checked": True,
                                "source": "USDA"
                            }
                    
                    # Results found but no good match
                    print(f"  USDA: '{ingredient_name}' - results found but no close match")
                    return {"valid": False, "checked": True, "source": "USDA-no-match"}
                
                # No results - DON'T reject immediately, let fallback handle it
                print(f"  USDA: No results for '{ingredient_name}' - trying fallback")
                return {"checked": False}  # Changed from valid:False to checked:False
            
            elif response.status_code == 400:
                print(f" USDA 400 Error - trying fallback")
                return {"checked": False}
            
            elif response.status_code == 403:
                print(" USDA API Key Invalid or Expired")
                return {"checked": False}
            
            else:
                print(f"  USDA returned {response.status_code}")
                return {"checked": False}
                
        except requests.exceptions.Timeout:
            print("  USDA API Timeout")
            return {"checked": False}
        
        except Exception as e:
            print(f"  USDA Error: {str(e)}")
            return {"checked": False}
    
    def _similarity_check(self, str1, str2):
        """Simple similarity check"""
        str1_words = set(str1.split())
        str2_words = set(str2.split())
        
        # Check if any word matches
        return len(str1_words & str2_words) > 0
    
    def _check_common_foods(self, ingredient_name):
        """Fallback validation using expanded common foods list"""
        # Direct match
        if ingredient_name in self.common_foods:
            print(f" Fallback: '{ingredient_name}' is a known food")
            return {
                "valid": True,
                "is_condiment": False,
                "checked": True,
                "source": "fallback-common"
            }
        
        # Check if it's a condiment
        if ingredient_name in self.common_condiments:
            print(f" Fallback: '{ingredient_name}' is a condiment")
            return {
                "valid": True,
                "is_condiment": True,
                "checked": True,
                "source": "fallback-condiment"
            }
        
        # Partial match check (e.g., "chicken breast" matches "chicken")
        for known_food in self.common_foods:
            if known_food in ingredient_name or ingredient_name in known_food:
                print(f" Fallback: '{ingredient_name}' partially matches '{known_food}'")
                return {
                    "valid": True,
                    "is_condiment": False,
                    "checked": True,
                    "source": "fallback-partial"
                }
        
        # Check condiments with partial match
        for condiment in self.common_condiments:
            if condiment in ingredient_name or ingredient_name in condiment:
                print(f" Fallback: '{ingredient_name}' partially matches condiment '{condiment}'")
                return {
                    "valid": True,
                    "is_condiment": True,
                    "checked": True,
                    "source": "fallback-condiment-partial"
                }
        
        # Not found anywhere
        print(f" Fallback: '{ingredient_name}' is NOT a recognized food")
        return {
            "valid": False,
            "is_condiment": False,
            "checked": True,
            "source": "fallback-invalid"
        }
    
    def validate_recipe_ingredients(self, ingredients):
        """Validate all ingredients"""
        if not ingredients or len(ingredients) == 0:
            return False, "No ingredients provided"
        
        invalid_items = []
        has_main_ingredient = False
        
        for item in ingredients:
            ingredient_name = item.get('name', '').strip()
            
            if not ingredient_name:
                continue
            
            result = self.is_valid_ingredient(ingredient_name)
            
            if not result['valid']:
                invalid_items.append(ingredient_name)
            elif not result.get('is_condiment', False):
                has_main_ingredient = True
        
        # Check invalid
        if invalid_items:
            return False, f"These items are not recognized as food ingredients: {', '.join(invalid_items)}"
        
        # Check condiments only
        if not has_main_ingredient:
            return False, "Please add at least one main ingredient (vegetables, meat, grains, dairy, fruits, etc.)"
        
        print(f" Validation passed: {len(ingredients)} ingredients OK")
        return True, None

# ============================================================================
# MAIN RECIPE CONTROLLER - FIXED JSON PARSING
# ============================================================================

validator = IngredientValidator()

def generate_recipe_controller(user_id, data):
    """Enhanced recipe controller with validation and robust JSON parsing"""
    
    ingredients = data.get('ingredients')
    cuisine = data.get('cuisine_preference')
    people = data.get('number_of_people')
    cooking_time = data.get('cooking_time')
    preference = data.get('cooking_preference')

    # Basic validation
    if not all([ingredients, cuisine, people, cooking_time, preference]):
        return {"status": "error", "message": "Required fields are missing."}, 400

    # INGREDIENT VALIDATION
    print(f" Validating {len(ingredients)} ingredients...")
    is_valid, error_message = validator.validate_recipe_ingredients(ingredients)
    
    if not is_valid:
        print(f" Validation failed: {error_message}")
        return {
            "status": "error", 
            "message": error_message,
            "error_type": "invalid_ingredients"
        }, 400

    items_list = ", ".join([f"{i['name']} ({i['qty']})" for i in ingredients])
    ingredients_json = json.dumps(ingredients, sort_keys=True, separators=(',', ':'))

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            check_sql = "SELECT id FROM user_queries WHERE user_id = %s"
            cursor.execute(check_sql, (user_id,))
            existing_record = cursor.fetchone()
            
            cursor.fetchall()  

            if existing_record:
                update_sql = """
                    UPDATE user_queries 
                    SET ingredients = %s, cuisine_preference = %s, number_of_people = %s, 
                        cooking_time = %s, cooking_preference = %s, created_at = CURRENT_TIMESTAMP 
                    WHERE id = %s
                """
                cursor.execute(update_sql, (ingredients_json, cuisine, people, cooking_time, preference, existing_record[0]))
            else:
                insert_sql = """
                    INSERT INTO user_queries 
                    (user_id, ingredients, cuisine_preference, number_of_people, cooking_time, cooking_preference) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_sql, (user_id, ingredients_json, cuisine, people, cooking_time, preference))
            
            conn.commit()
            cursor.close() 
        except Exception as db_err:
            print(f"Database Error (user_queries): {str(db_err)}")

    dynamic_limit = random.randint(4, 16)
    
    prompt = f"""
You are a creative world-class chef.

INGREDIENTS: {items_list}
CUISINE: {cuisine}
PEOPLE: {people}
TIME LIMIT: {cooking_time}
OCCASION: {preference}

Generate EXACTLY {dynamic_limit} unique recipes using these ingredients.

Rules:
- Focus on the provided ingredients
- Match the cuisine and occasion
- Keep cooking time within limit
- Be creative and diverse
- IMPORTANT: Always include 'min' after the cooking_time value (e.g., "20 min")
- CRITICAL: Return ONLY a valid JSON array, NO nested structures

Output format (STRICT):
[
  {{
    "menu_name": "Dish Name",
    "description": "Brief 2-3 line description",
    "cooking_time": "Time in minutes (must end with 'min')"
  }},
  {{
    "menu_name": "Another Dish",
    "description": "Brief description",
    "cooking_time": "25 min"
  }}
]

DO NOT wrap in any other object. DO NOT use nested arrays. Just return the array directly.
"""

    api_url = os.getenv("MISTRAL_API_URL")
    model = os.getenv("MISTRAL_MODEL")

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_predict": 3000
        }
    }

    headers = {"Content-Type": "application/json"}

    try:
        print(f" Generating {dynamic_limit} recipes...")
        response = requests.post(api_url, json=payload, headers=headers, timeout=700)
        
        if response.status_code != 200:
            print(f" Mistral API error: {response.status_code}")
            return {"status": "error", "message": f"AI API error: {response.status_code}"}, 500
        
        result = response.json()
        raw_content = result.get('response', '')
        
        if not raw_content:
            print(" AI returned empty response")
            return {"status": "error", "message": "AI returned empty content."}, 500

        # ROBUST JSON CLEANING
        raw_content = raw_content.strip()
        
        # Remove markdown code blocks
        if raw_content.startswith('```'):
            raw_content = raw_content.split('```json')[-1].split('```')[0].strip()
        
        print(f" AI Response (first 200 chars): {raw_content[:200]}")
        
        # Try to parse
        try:
            recipes_data = json.loads(raw_content)
        except json.JSONDecodeError as je:
            # FALLBACK: Try to extract array from malformed JSON
            print(f" Initial JSON parse failed: {str(je)}")
            print(" Attempting to extract valid JSON array...")
            
            # Find first [ and last ]
            start_idx = raw_content.find('[')
            end_idx = raw_content.rfind(']')
            
            if start_idx != -1 and end_idx != -1:
                array_content = raw_content[start_idx:end_idx+1]
                try:
                    recipes_data = json.loads(array_content)
                    print(" Successfully extracted array from malformed JSON")
                except:
                    print(" Could not extract valid JSON")
                    return {"status": "error", "message": "AI returned invalid JSON format."}, 500
            else:
                return {"status": "error", "message": "AI returned invalid JSON format."}, 500

        # HANDLE DIFFERENT JSON STRUCTURES
        recipes = None
        
        # Case 1: Already a list
        if isinstance(recipes_data, list):
            recipes = recipes_data
            print(f" Format: Direct array with {len(recipes)} items")
        
        # Case 2: Dict with known keys
        elif isinstance(recipes_data, dict):
            # Try common keys
            for key in ["recipes", "Recipes", "data", "Data", "items", "Items"]:
                if key in recipes_data:
                    recipes = recipes_data[key]
                    print(f" Format: Dict with key '{key}'")
                    break
            
            # If still not found, take first list value
            if not recipes:
                for value in recipes_data.values():
                    if isinstance(value, list):
                        recipes = value
                        print(" Format: Dict with unnamed list value")
                        break
        
        # Validation
        if not isinstance(recipes, list) or len(recipes) == 0:
            print(" AI returned invalid format")
            print(f"Full response: {json.dumps(recipes_data, indent=2)}")
            return {"status": "error", "message": "AI did not generate valid recipes."}, 500

        # CLEAN RECIPE ITEMS - Handle both dict and nested array formats
        cleaned_recipes = []
        for item in recipes:
            if isinstance(item, dict):
                # Normal dict format
                cleaned_recipes.append(item)
            elif isinstance(item, list) and len(item) >= 2:
                # Nested array format: ["Name", {"description": ..., "cooking_time": ...}]
                name = item[0]
                details = item[1] if isinstance(item[1], dict) else {}
                cleaned_recipes.append({
                    "menu_name": name,
                    "description": details.get("description", ""),
                    "cooking_time": details.get("cooking_time", "30 min")
                })
            else:
                # Skip invalid items
                print(f" Skipping invalid recipe item: {item}")
                continue

        recipes = cleaned_recipes
        
        if len(recipes) == 0:
            return {"status": "error", "message": "No valid recipes could be extracted."}, 500

        # Add images
        for recipe in recipes:
            name = recipe.get('menu_name', 'food')
            clean_name = "".join(char for char in name if char.isalnum() or char.isspace())
            search_query = clean_name.replace(" ", ",")
            recipe['image_url'] = f"https://image.pollinations.ai/prompt/{search_query}%20food%20realistic?width=800&height=600&nologo=true"
        
        # Save to database
        if conn:
            try:
                save_cursor = conn.cursor()
                all_recipes_json = json.dumps(recipes)

                new_table_sql = """
                    INSERT INTO generated_recipes 
                    (user_id, ingredients, cuisine_preference, number_of_people, cooking_time, cooking_preference, recipe_list) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                save_cursor.execute(new_table_sql, (
                    user_id, ingredients_json, cuisine, people, cooking_time, preference, all_recipes_json
                ))
                conn.commit()
                save_cursor.fetchall()  
                save_cursor.close()
                print(" Saved to database")
            except Exception as e_db:
                print(f" DB save failed: {str(e_db)}")
            finally:
                if conn:
                    conn.close()

        print(f" Generated {len(recipes)} recipes successfully")
        return {
            "status": "success",
            "user_id": user_id,
            "data": {
                "recipes": recipes,
                "total_recipes": len(recipes)
            }
        }, 200

    except json.JSONDecodeError as je:
        if conn: conn.close()
        print(f" JSON decode error: {str(je)}")
        print(f"Raw content: {raw_content[:500]}")
        return {"status": "error", "message": "AI returned invalid JSON format."}, 500
    
    except Exception as e:
        if conn: conn.close()
        print(f" Error: {str(e)}")
        return {"status": "error", "message": f"AI Analysis failed: {str(e)}"}, 500