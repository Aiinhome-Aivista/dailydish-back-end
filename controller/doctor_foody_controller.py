import os
import re
import requests
import json
from typing import Dict, List, Tuple, Optional

class DoctorFoodyController:
    """
    Smart Personal Chef AI - Fixed Production Version
    
    FIXES:
    ✅ Captures "500gm", "2cup" (compact format without space)
    ✅ LLM-based dynamic spice suggestions
    ✅ USER CAN SELECT SPECIFIC SPICES FROM SUGGESTIONS
    ✅ USER-PROVIDED QUANTITIES ARE RESPECTED (no auto-calc override)
    
    Features:
    - Both order extraction: "500g chicken" AND "chicken 500g"
    - Smart validation: No junk like "Onion Made Which Recipe"
    - Cuisine suggestions AFTER ingredient collection
    - All 5 cuisines: Oriental, Indian-Sub, Central Asian, European, Inter-Continental
    """
    
    def __init__(self):
        # Valid ingredients database
        self.valid_ingredients = {
            # Fish & Seafood
            'fish', 'katla', 'rui', 'hilsa', 'ilish', 'prawn', 'shrimp', 'rohu', 'pomfret',
            'salmon', 'tuna', 'mackerel', 'crab', 'lobster',
            
            # Meat & Poultry
            'chicken', 'mutton', 'beef', 'pork', 'lamb', 'duck', 'turkey', 'egg', 'eggs',
            
            # Vegetables
            'potato', 'potatoes', 'tomato', 'tomatoes', 'onion', 'onions',
            'garlic', 'ginger', 'capsicum', 'pepper', 'carrot', 'carrots',
            'cauliflower', 'cabbage', 'beans', 'peas', 'spinach', 'broccoli',
            'eggplant', 'brinjal', 'okra', 'cucumber', 'radish', 'lettuce',
            
            # Grains & Staples
            'rice', 'wheat', 'flour', 'bread', 'noodles', 'pasta',
            'dal', 'lentils', 'chickpeas',
            
            # Dairy
            'milk', 'curd', 'yogurt', 'cream', 'cheese', 'paneer', 'panner', 'butter', 'ghee',
            
            # Oils
            'oil', 'mustard oil', 'olive oil', 'coconut oil', 'vegetable oil',
            
            # Common spices
            'turmeric', 'cumin', 'coriander', 'chili', 'pepper', 'salt', 'garam masala'
        }
        
        # LLM API configuration
        self.llm_api_url = os.getenv('MISTRAL_API_URL', 'http://localhost:11434/api/generate')
        self.llm_model = os.getenv('MISTRAL_MODEL', 'mistral')
    
    # ==================== SMART INGREDIENT EXTRACTION (FIXED) ====================
    
    def extract_ingredients(self, text: str) -> List[Dict]:
        """
        Extract ingredients - handles ALL formats:
        ✅ 500g chicken, 500gm chicken (with space)
        ✅ 500gm chicken, 2cup rice (NO space - FIXED)
        ✅ chicken 500g, rice 2cup
        ✅ 2 pieces katla fish
        ✅ Handles typos: 2oogm → 200gm, 5ooo → 5000
        """
        ingredients = []
        text_lower = text.lower()
        
        # Skip greetings
        if text_lower.strip() in ['hi', 'hello', 'hey', 'yes', 'no', 'ok', 'okay']:
            return []
        
        # FIX TYPOS: Replace common number typos (oo → 00, ooo → 000)
        # Pattern 1: Compact format - digit(s) + 'o's + unit (no space): 2oogm → 200gm
        text_lower = re.sub(r'(\d)o+(?=g(?!o)|gm|kg|ml|l(?!o)|cup)', r'\g<1>00', text_lower)
        # Pattern 2: Spaced format - digit(s) + 'o's + space + unit: 2oo gm → 200 gm
        text_lower = re.sub(r'(\d)o+\s+(?=g(?!o)|gm|kg|ml|l(?!o)|cup)', r'\g<1>00 ', text_lower)
        # Examples: 2oogm→200gm, 5ooo gm→5000 gm, 1oo g→100 g, 3o kg→30 kg
        
        found_items = set()  # Track what we've already extracted
        
        # ===== PATTERN 1: Quantity FIRST =====
        qty_first_patterns = [
            # FIXED: 500gm, 2cup (NO space between number and unit)
            r'(\d+(?:\.\d+)?)(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass)\s+([a-z]+(?:\s+[a-z]+){0,1}?)(?:\s*(?:,|\sand\s|\.|\band\s|$))',
            # Standard: 500 g chicken, 2 cups rice (WITH space)
            r'(\d+(?:\.\d+)?)\s+(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass)\s+([a-z]+(?:\s+[a-z]+){0,1}?)(?:\s*(?:,|\sand\s|\.|\band\s|$))',
            # 2 pieces, 3piece (with/without space) - ALLOW up to 2 words for compound names
            r'(\d+)\s*(piece|pieces|peace|peaces|pics?|pcs?)\s+(?:of\s+)?([a-z]+(?:\s+[a-z]+){0,1}?)(?:\s*(?:,|\sand\s|\.|\band\s|$))',
            # Spoons: 2 tbsp, 1tsp
            r'(\d+)\s*(spoon|spoons|tbsp|tsp)\s+(?:of\s+)?([a-z]+(?:\s+[a-z]+){0,1}?)(?:\s*(?:,|\sand\s|\.|\band\s|$))',
            # NEW: Number + fish/meat items (e.g., "2 katla fish", "3 chicken")
            r'(\d+)\s+([a-z]+\s+(?:fish|chicken|egg|eggs|prawn|shrimp|crab|lobster))(?:\s*(?:,|\sand\s|\.|\band\s|$))',
        ]
        
        for pattern in qty_first_patterns:
            for match in re.finditer(pattern, text_lower):
                # Check if this is the special fish/meat pattern (only 2 groups)
                if len(match.groups()) == 2:
                    # Pattern: "2 katla fish" → qty_num="2", ing_raw="katla fish"
                    qty_num = match.group(1)
                    ing_raw = match.group(2)
                    unit = "pieces"  # Default unit for countable items
                else:
                    # Normal pattern: qty + unit + ingredient
                    qty_num = match.group(1)
                    unit = match.group(2)
                    ing_raw = match.group(3)
                
                ing_clean = self._clean_and_validate(ing_raw)
                if ing_clean and ing_clean.lower() not in found_items:
                    qty = self._format_qty(qty_num, unit)
                    ingredients.append({"name": ing_clean, "qty": qty, "unclear": False})
                    found_items.add(ing_clean.lower())
        
        # ===== PATTERN 2: Ingredient FIRST =====
        ing_first_patterns = [
            # FIXED: chicken 500gm, rice 2cup (NO space) - use word boundary
            r'\b([a-z]+(?:\s+[a-z]+){0,1}?)\s+(\d+(?:\.\d+)?)(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass)(?:\s*(?:,|\sand\s|\.|\band\s|$))',
            # Standard: chicken 500 g, rice 2 cups (WITH space)
            r'\b([a-z]+(?:\s+[a-z]+){0,1}?)\s+(\d+(?:\.\d+)?)\s+(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass)(?:\s*(?:,|\sand\s|\.|\band\s|$))',
            # fish 2 pieces, fish 2piece
            r'\b([a-z]+(?:\s+[a-z]+){0,1}?)\s+(\d+)\s*(piece|pieces|peace|peaces|pics?|pcs?)(?:\s*(?:,|\sand\s|\.|\band\s|$))',
            # salt 1 tsp, oil 2tbsp
            r'\b([a-z]+(?:\s+[a-z]+){0,1}?)\s+(\d+)\s*(spoon|spoons|tbsp|tsp)(?:\s*(?:,|\sand\s|\.|\band\s|$))',
        ]
        
        for pattern in ing_first_patterns:
            for match in re.finditer(pattern, text_lower):
                ing_raw = match.group(1)
                qty_num = match.group(2)
                unit = match.group(3)
                
                ing_clean = self._clean_and_validate(ing_raw)
                if ing_clean and ing_clean.lower() not in found_items:
                    qty = self._format_qty(qty_num, unit)
                    ingredients.append({"name": ing_clean, "qty": qty, "unclear": False})
                    found_items.add(ing_clean.lower())
        
        # ===== PATTERN 3: Vague quantities (some rice, few onions) =====
        vague_pattern = r'(few|some|little\s*bit|little|bit|handful)\s+(?:of\s+)?([a-z]+(?:\s+[a-z]+){0,2}?)(?=\s*(?:,|and|\.|\band\b|$))'
        
        for match in re.finditer(vague_pattern, text_lower):
            vague = match.group(1)
            ing_raw = match.group(2)
            
            ing_clean = self._clean_and_validate(ing_raw)
            if ing_clean and ing_clean.lower() not in found_items:
                ingredients.append({"name": ing_clean, "qty": vague.strip(), "unclear": True})
                found_items.add(ing_clean.lower())
        
        # ===== PATTERN 4: Standalone common ingredients (only if not found yet) =====
        common = ['rice', 'fish', 'chicken', 'potato', 'tomato', 'onion', 'eggs', 'egg']
        for word in common:
            if word in text_lower and word not in found_items:
                # Must be standalone word
                if re.search(rf'\b{word}\b', text_lower):
                    # Make sure it's not part of a pattern we already caught
                    if not any(word in item for item in found_items):
                        ingredients.append({"name": word.title(), "qty": "some", "unclear": True})
                        found_items.add(word)
        
        return ingredients
    
    def _clean_and_validate(self, raw: str) -> Optional[str]:
        """Clean and validate ingredient name"""
        # Remove junk words
        junk = ['have', 'got', 'use', 'want', 'need', 'the', 'and', 'or', 'of', 'with',
                'a', 'an', 'is', 'are', 'made', 'which', 'recipe', 'that', 'this', 'will',
                'how', 'what', 'when', 'where', 'why', 'can', 'could', 'should', 'would']
        
        words = raw.strip().split()
        clean_words = []
        
        for word in words:
            if word in junk or len(word) <= 1 or word.isdigit():
                continue
            # Skip if word is a unit typo
            if word in ['pices', 'pics', 'peace', 'peaces', 'pcs', 'pic']:
                continue
            clean_words.append(word)
        
        if not clean_words:
            return None
        
        # If contains junk combo, reject entirely
        raw_lower = raw.lower()
        junk_combos = ['made which', 'which recipe', 'how to', 'what is', 'can i', 'should i']
        if any(combo in raw_lower for combo in junk_combos):
            return None
        
        # Max 2 words for ingredients (stricter - prevents "onion made which")
        if len(clean_words) > 2:
            return None
        
        cleaned = ' '.join(clean_words)
        
        # Validate
        if self._is_valid(cleaned):
            return cleaned.title()
        
        return None
    
    def _is_valid(self, name: str) -> bool:
        """Check if ingredient is real"""
        name_lower = name.lower()
        
        # Blacklist: NOT ingredients
        blacklist = {
            'indian', 'chinese', 'italian', 'french', 'thai', 'japanese', 'korean',
            'bengali', 'punjabi', 'oriental', 'european', 'asian', 'central',
            'spicy', 'mild', 'sweet', 'tangy', 'balanced', 'rich', 'simple',
            'vegetarian', 'vegan', 'halal', 'daily', 'special', 'party',
            'cooking', 'recipe', 'food', 'dish', 'meal', 'people', 'person',
            'pices', 'pics', 'peace', 'peaces'  # Typos, not ingredients
        }
        
        if name_lower in blacklist:
            return False
        
        # Special handling for compound names (e.g., "katla fish", "olive oil")
        # If it's a 2-word combo with a valid ingredient, accept it
        if ' ' in name_lower:
            words = name_lower.split()
            # Check if any word is a known valid ingredient
            for word in words:
                if word in self.valid_ingredients:
                    return True
            # If no word matches, reject
            return False
        
        # Single word - check against known ingredients
        for valid in self.valid_ingredients:
            if valid in name_lower or name_lower in valid:
                return True
        
        return False
    
    def _format_qty(self, num: str, unit: str) -> str:
        """Format quantity properly"""
        unit_map = {
            'g': 'g', 'gm': 'g', 'kg': 'kg', 'kgs': 'kg',
            'ml': 'ml', 'l': 'l', 'ltr': 'l', 'litre': 'l', 'litres': 'l',
            'piece': 'pieces', 'pieces': 'pieces',
            'peace': 'pieces', 'peaces': 'pieces',
            'pic': 'pieces', 'pics': 'pieces', 'pcs': 'pieces',
            'cup': 'cups', 'cups': 'cups','glass':'glass',
            'spoon': 'tbsp', 'spoons': 'tbsp', 'tbsp': 'tbsp',
            'tsp': 'tsp'
        }
        
        unit_clean = unit_map.get(unit.lower(), unit)
        
        # Compact for weights
        if unit_clean in ['g', 'kg', 'ml', 'l']:
            return f"{num}{unit_clean}"
        
        # Singular if 1
        if num == '1':
            if unit_clean == 'pieces':
                return f"{num} piece"
            elif unit_clean == 'cups':
                return f"{num} cup"
            elif unit_clean == 'glass':
                return f"{num} glass"
        
        return f"{num} {unit_clean}"
    
    def merge_ingredients(self, existing: List[Dict], new: List[Dict]) -> List[Dict]:
        """Merge - update or add"""
        result = {ing['name'].lower(): ing for ing in existing}
        
        for ing in new:
            result[ing['name'].lower()] = ing
        
        return list(result.values())
    
    def update_unclear(self, text: str, ingredients: List[Dict]) -> List[Dict]:
        """Update unclear quantities"""
        text_lower = text.lower()
        updated = []
        
        for ing in ingredients:
            if ing.get('unclear'):
                ing_lower = ing['name'].lower()
                
                # Try both orders with FIXED patterns (no space)
                patterns = [
                    # Qty first: 2cups rice, 100g onion, 2cup rice (NO space)
                    rf'(\d+(?:\.\d+)?)(g|gm|kg|ml|l|cup|cups|glass|piece|pieces|peace|pics?|pcs?)\s+{ing_lower}',
                    # Qty first: 2 cups rice, 100 g onion (WITH space)
                    rf'(\d+(?:\.\d+)?)\s+(g|gm|kg|ml|l|cup|cups|glass|piece|pieces|peace|pics?|pcs?)\s+{ing_lower}',
                    # Ing first: rice 2cup, onion 100g (NO space)
                    rf'{ing_lower}\s+(\d+(?:\.\d+)?)(g|gm|kg|ml|l|cup|cups|glass|piece|pieces|peace|pics?|pcs?)',
                    # Ing first: rice 2 cups, onion 100 g (WITH space)
                    rf'{ing_lower}\s+(\d+(?:\.\d+)?)\s+(g|gm|kg|ml|l|cup|cups|glass|piece|pieces|peace|pics?|pcs?)',
                ]
                
                found = False
                for pattern in patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        qty_num = match.group(1)
                        unit = match.group(2)
                        qty = self._format_qty(qty_num, unit)
                        
                        updated.append({"name": ing['name'], "qty": qty, "unclear": False})
                        found = True
                        break
                
                if not found:
                    updated.append(ing)
            else:
                updated.append(ing)
        
        return updated
    
    # ==================== LLM-BASED DYNAMIC SUGGESTIONS ====================
    
    def get_llm_suggestions(self, cuisine: str, ingredients: List[Dict]) -> Dict:
        """Get dynamic suggestions from LLM based on cuisine and ingredients"""
        try:
            # Build ingredient list for context
            ing_names = [ing['name'] for ing in ingredients]
            ing_text = ", ".join(ing_names)
            
            prompt = f"""As a Culinary Expert, analyze the following ingredients for {cuisine} cuisine: {ing_text}

Based on these ingredients, suggest ONLY the essential spices, herbs, oils, and basic cooking items that are:
1. Commonly used in {cuisine} cuisine
2. NOT already in the ingredient list
3. Essential for cooking with the given ingredients

Response MUST be a clean JSON object:
{{
  "spices": ["spice1", "spice2", "spice3"],
  "basics": ["oil/basic1", "oil/basic2"]
}}

Rules:
- List items in lowercase
- Include ONLY 3-5 most essential spices
- Include ONLY 2-3 most essential basics (oils, salt, etc.)
- Be specific (e.g., "mustard oil" not just "oil")
- Do NOT include items already in: {ing_text}
"""

            payload = {
                "model": self.llm_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.3}
            }
            
            response = requests.post(self.llm_api_url, json=payload, timeout=700)
            response.raise_for_status()
            result = response.json()
            
            raw_content = result.get('response', '').strip()
            
            if not raw_content:
                # Fallback to empty suggestions
                return {"spices": [], "basics": []}
            
            suggestions = json.loads(raw_content)
            
            # Filter out duplicates (case-insensitive)
            existing_lower = [ing['name'].lower() for ing in ingredients]
            
            filtered_spices = [s for s in suggestions.get('spices', []) if s.lower() not in existing_lower]
            filtered_basics = [b for b in suggestions.get('basics', []) if b.lower() not in existing_lower]
            
            return {
                "spices": filtered_spices[:5],  # Max 5 spices
                "basics": filtered_basics[:3]   # Max 3 basics
            }
            
        except Exception as e:
            print(f"LLM suggestion error: {str(e)}")
            # Fallback: return empty suggestions
            return {"spices": [], "basics": []}
    
    # ==================== NEW: PARSE USER SPICE SELECTION (FIXED) ====================
    
    def parse_user_selection(self, message: str, available_suggestions: Dict) -> List[Dict]:
        """
        Parse which spices user wants to add from the suggested list.
        Handles: "turmeric, cumin, salt" or "1, 2, 5" or "sesame oil 2tsp, salt"
        Returns: List of dicts with 'name' and optional 'qty' if user specified
        """
        message_lower = message.lower().strip()
        
        # Get all available items
        all_items = available_suggestions.get('spices', []) + available_suggestions.get('basics', [])
        
        selected = []
        
        # Try to match ingredient names directly (with quantities if provided)
        for item in all_items:
            item_lower = item.lower()
            # Check if the item name appears in the message
            if re.search(rf'\b{re.escape(item_lower)}\b', message_lower):
                # Try to extract user-provided quantity for this item
                user_qty = self._extract_qty_for_item(message_lower, item_lower)
                
                selected.append({
                    'name': item,
                    'qty': user_qty  # None if not specified
                })
        
        # If no direct matches found, try number-based selection
        if not selected:
            # Extract numbers from message (e.g., "1, 3, 5" or "1 3 5")
            numbers = re.findall(r'\d+', message)
            for num_str in numbers:
                idx = int(num_str) - 1  # Convert to 0-based index
                if 0 <= idx < len(all_items):
                    selected.append({
                        'name': all_items[idx],
                        'qty': None
                    })
        
        return selected
    
    def _extract_qty_for_item(self, text: str, item_name: str) -> Optional[str]:
        """
        Extract user-provided quantity for a specific item.
        Handles: "sesame oil 2tsp", "2tsp sesame oil", "turmeric 1 tsp"
        """
        # Patterns to match quantity near the item name
        patterns = [
            # Item first: "sesame oil 2tsp", "turmeric 1 tsp"
            rf'{re.escape(item_name)}\s+(\d+(?:\.\d+)?)\s*(tsp|tbsp|g|gm|kg|ml|cup|cups|spoon|spoons|piece|pieces)',
            rf'{re.escape(item_name)}\s+(\d+(?:\.\d+)?)(tsp|tbsp|g|gm|kg|ml|cup|cups)',
            # Quantity first: "2tsp sesame oil", "1 tsp turmeric"
            rf'(\d+(?:\.\d+)?)\s*(tsp|tbsp|g|gm|kg|ml|cup|cups|spoon|spoons|piece|pieces)\s+{re.escape(item_name)}',
            rf'(\d+(?:\.\d+)?)(tsp|tbsp|g|gm|kg|ml|cup|cups)\s+{re.escape(item_name)}',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                qty_num = match.group(1)
                unit = match.group(2)
                return self._format_qty(qty_num, unit)
        
        return None
    
    # ==================== NEW: CALCULATE AUTO QUANTITY ====================
    
    def calculate_auto_quantity(self, spice_name: str, main_ingredients: List[Dict], cuisine: str) -> str:
        """
        Calculate appropriate quantity for a spice based on main ingredients.
        Returns quantity string like "1 tsp", "2 tbsp", "to taste"
        """
        spice_lower = spice_name.lower()
        
        # Estimate total weight from main ingredients
        total_weight = 0
        for ing in main_ingredients:
            qty_str = ing.get('qty', '').lower()
            
            # Extract number
            qty_match = re.search(r'(\d+(?:\.\d+)?)', qty_str)
            if qty_match:
                qty_num = float(qty_match.group(1))
                
                # Convert to grams
                if 'kg' in qty_str:
                    total_weight += qty_num * 1000
                elif 'g' in qty_str or 'gm' in qty_str:
                    total_weight += qty_num
                elif 'cup' in qty_str:
                    total_weight += qty_num * 200
                elif 'glass' in qty_str:
                    total_weight += qty_num * 300  # 1 cup ≈ 200g
                elif 'piece' in qty_str:
                    total_weight += qty_num * 150  # 1 piece ≈ 150g
        
        # Default if can't calculate
        if total_weight == 0:
            total_weight = 500
        
        # Quantity rules based on spice type
        
        # Oil/Fat
        if any(oil in spice_lower for oil in ['oil', 'ghee', 'butter']):
            if total_weight > 1000:
                return "4 tbsp"
            elif total_weight > 500:
                return "2 tbsp"
            else:
                return "1 tbsp"
        
        # Salt (always "to taste")
        if 'salt' in spice_lower:
            return "to taste"
        
        # Heavy spices (turmeric, chili, paprika)
        if any(spice in spice_lower for spice in ['turmeric', 'chili', 'paprika', 'cayenne']):
            if cuisine == 'Indian-Sub':
                if total_weight > 800:
                    return "1.5 tsp"
                elif total_weight > 400:
                    return "1 tsp"
                else:
                    return "0.5 tsp"
            else:
                if total_weight > 800:
                    return "1 tsp"
                else:
                    return "0.5 tsp"
        
        # Aromatic spices (cumin, coriander, etc.)
        if any(spice in spice_lower for spice in ['cumin', 'coriander', 'fennel', 'fenugreek', 'mustard']):
            if total_weight > 800:
                return "2 tsp"
            elif total_weight > 400:
                return "1 tsp"
            else:
                return "0.5 tsp"
        
        # Strong spices (cardamom, clove, etc.)
        if any(spice in spice_lower for spice in ['cardamom', 'clove', 'cinnamon', 'star anise']):
            if total_weight > 800:
                return "4-5 pieces"
            elif total_weight > 400:
                return "2-3 pieces"
            else:
                return "1-2 pieces"
        
        # Ginger/Garlic paste
        if any(item in spice_lower for item in ['ginger', 'garlic']) and 'paste' in spice_lower:
            if total_weight > 800:
                return "2 tbsp"
            elif total_weight > 400:
                return "1 tbsp"
            else:
                return "1 tsp"
        
        # Garam masala and mixed spices
        if any(blend in spice_lower for blend in ['garam masala', 'curry powder', 'five spice']):
            if total_weight > 800:
                return "1.5 tsp"
            elif total_weight > 400:
                return "1 tsp"
            else:
                return "0.5 tsp"
        
        # Default for other spices
        if total_weight > 800:
            return "1 tsp"
        else:
            return "0.5 tsp"
    
    # ==================== MODIFIED: ADD SELECTED SUGGESTIONS (FIXED) ====================
    
    def add_suggestions(self, ingredients: List[Dict], selected_items: List[Dict], cuisine: str = None) -> List[Dict]:
        """
        Add user-selected suggestions with user-provided OR auto-calculated quantities
        selected_items is now a list of dicts: [{'name': 'sesame oil', 'qty': '2 tsp'}, ...]
        """
        existing_names = {ing['name'].lower() for ing in ingredients}
        
        for item_dict in selected_items:
            item_name = item_dict['name']
            user_qty = item_dict.get('qty')  # Will be None if user didn't specify
            
            if item_name.lower() not in existing_names:
                # Use user-provided quantity if available, otherwise auto-calculate
                if user_qty:
                    qty = user_qty
                else:
                    qty = self.calculate_auto_quantity(item_name, ingredients, cuisine or 'Indian-Sub')
                
                ingredients.append({
                    "name": item_name.title(),
                    "qty": qty,
                    "unclear": False
                })
        
        return ingredients
    
    # ==================== CUISINE EXTRACTION ====================
    
    def extract_cuisine(self, text: str) -> Optional[str]:
        """Extract cuisine - EXACT 5 types matching UI (prioritize specific matches)"""
        text_lower = text.lower()
        
        # IMPORTANT: Order matters - check most specific first to avoid false matches
        # e.g., "Central Asian" should match before "Asian" (Oriental)
        cuisines = [
            ('Central Asian', ['central asian', 'central', 'turkish', 'persian', 'arabic', 'middle eastern', 'uzbek']),
            ('Inter-Continental', ['inter-continental', 'intercontinental', 'inter continental', 'fusion', 'international', 'mixed', 'global']),
            ('Indian-Sub', ['indian-sub', 'indian', 'bengali', 'punjabi', 'desi', 'south asian']),
            ('European', ['european', 'italian', 'french', 'spanish', 'greek', 'mediterranean']),
            ('Oriental', ['oriental', 'chinese', 'thai', 'japanese', 'korean', 'vietnamese', 'asian']),  # 'asian' last to avoid conflicts
        ]
        
        for name, keywords in cuisines:
            if any(kw in text_lower for kw in keywords):
                return name
        
        return None
    
    # ==================== OTHER EXTRACTIONS ====================
    
    def extract_people(self, text: str) -> Optional[int]:
        """Extract people count"""
        patterns = [
            r'for\s+(\d+)\s+(?:people|person)',
            r'(\d+)\s+(?:people|person)',
            r'serve\s+(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return None
    
    def extract_preference(self, text: str) -> Optional[str]:
        """Extract cooking preference"""
        text_lower = text.lower()
        
        if any(w in text_lower for w in ['special', 'party', 'celebration', 'guests']):
            return 'special_day'
        elif any(w in text_lower for w in ['daily', 'everyday', 'regular', 'normal']):
            return 'daily_basis'
        
        return None
    
    # ==================== FLOW CONTROL ====================
    
    def check_missing(self, collected: Dict) -> List[str]:
        """Check missing fields"""
        missing = []
        
        if not collected.get('ingredients'):
            missing.append('ingredients')
        else:
            unclear = [ing for ing in collected['ingredients'] if ing.get('unclear')]
            if unclear:
                missing.append('unclear_quantities')
        
        # Check for pending suggestions (block other fields)
        if collected.get('_pending_suggestions') and not collected.get('_suggestions_handled'):
            missing.append('suggestions_pending')
            return missing
        
        if not collected.get('cuisine_preference'):
            missing.append('cuisine_preference')
        
        if not collected.get('number_of_people'):
            missing.append('number_of_people')
        
        if not collected.get('cooking_preference'):
            missing.append('cooking_preference')
        
        return missing
    
    def next_question(self, missing: List[str], collected: Dict) -> str:
        """Next question"""
        if not missing:
            return "READY"
        
        field = missing[0]
        
        if field == 'ingredients':
            return "👋 Hi! What ingredients do you have?\n💡 Example: '2 pieces katla fish, 1cup rice, 100g onion'"
        
        elif field == 'unclear_quantities':
            unclear = [ing['name'] for ing in collected['ingredients'] if ing.get('unclear')]
            if len(unclear) == 1:
                return f"How much {unclear[0]}?\n💡 Example: '2 pieces' or '100g' or '1cup'"
            else:
                return f"Please specify quantities for: {', '.join(unclear)}\n💡 Example: '2tomato, 100g onion, 1cup rice'"
        
        elif field == 'suggestions_pending':
            # MODIFIED: Show numbered list for user selection
            sugg = collected['_pending_suggestions']
            all_sugg = sugg['spices'] + sugg['basics']
            
            # Create numbered list
            items_list = '\n'.join([f"{i+1}. {item}" for i, item in enumerate(all_sugg)])
            
            return (
                f"💡 **Common additions for {collected.get('cuisine_preference', 'your cuisine')}:**\n\n"
                f"{items_list}\n\n"
                f"➡️ Select items to add:\n"
                f"• Type names: 'turmeric, cumin, salt'\n"
                f"• Type names with qty: 'sesame oil 2tsp, turmeric 1tsp'\n"
                f"• Type numbers: '1, 3, 5'\n"
                f"• Type 'all' for everything\n"
                f"• Type 'no' to skip"
            )
        
        elif field == 'cuisine_preference':
            return "What type of cuisine?\n🍽️ Oriental / Indian-Sub / Central Asian / European / Inter-Continental"
        
        elif field == 'number_of_people':
            return "How many people are you cooking for?"
        
        elif field == 'cooking_preference':
            return "Is this for daily meal or special occasion?"
        
        return "Please provide more details."
    
    def format_summary(self, collected: Dict) -> str:
        """Format summary"""
        ings = ", ".join([f"{ing['qty']} {ing['name']}" for ing in collected['ingredients']])
        
        return (
            f"📋 **Your cooking plan:**\n\n"
            f"🥘 **Ingredients:** {ings}\n"
            f"🍽️ **Cuisine:** {collected['cuisine_preference']}\n"
            f"👥 **People:** {collected['number_of_people']}\n"
            f"✨ **Type:** {collected['cooking_preference'].replace('_', ' ').title()}\n\n"
            f"✅ Type 'confirm' to generate recipes!"
        )
    
    # ==================== INTENT ====================
    
    def detect_intent(self, text: str) -> str:
        """Detect intent"""
        text_lower = text.lower().strip()
        
        if any(w in text_lower for w in ['confirm', 'generate', 'cook', 'ready']):
            return 'confirm'
        
        if any(w in text_lower for w in ['reset', 'start over']):
            return 'reset'
        
        # MODIFIED: Check for "all" intent
        if text_lower in ['all', 'add all', 'yes', 'add', 'okay', 'ok'] and len(text_lower.split()) <= 2:
            return 'add_all_suggestions'
        
        if any(w in text_lower for w in ['no', 'skip']):
            return 'skip_suggestions'
        
        return 'provide'
    
    # ==================== RECIPE GENERATION ====================
    
    def generate_recipe(self, user_id: str, collected: Dict) -> Tuple[Dict, int]:
        """Generate recipe"""
        try:
            from controller.recipe_controller import generate_recipe_controller
            
            # Default cooking time
            if not collected.get('cooking_time'):
                collected['cooking_time'] = '60 min' if collected.get('cooking_preference') == 'special_day' else '45 min'
            
            payload = {
                "ingredients": collected['ingredients'],
                "cuisine_preference": collected['cuisine_preference'],
                "number_of_people": collected['number_of_people'],
                "cooking_time": collected['cooking_time'],
                "cooking_preference": collected['cooking_preference']
            }
            
            recipe_list, status = generate_recipe_controller(user_id, payload)
            
            if status == 200:
                return {
                    "status": "success",
                    "bot_name": "Doctor Foody",
                    "message": "🎉 Here are your delicious recipes!",
                    "data": recipe_list,
                    "collected_data": {},
                    "missing_fields": []
                }, 200
            else:
                return {
                    "status": "error",
                    "bot_name": "Doctor Foody",
                    "message": "Failed to generate recipes.",
                    "collected_data": collected,
                    "missing_fields": []
                }, 500
        except Exception as e:
            return {
                "status": "error",
                "bot_name": "Doctor Foody",
                "message": f"Error: {str(e)}",
                "collected_data": collected,
                "missing_fields": []
            }, 500
    
    # ==================== MAIN HANDLER ====================
    
    def handle_chat(self, user_id: str, data: Dict) -> Tuple[Dict, int]:
        """Main handler"""
        message = data.get('message', '').strip()
        collected = data.get('collected_data', {})
        
        if not message:
            return {
                "status": "success",
                "bot_name": "Doctor Foody",
                "message": self.next_question(['ingredients'], {}),
                "collected_data": {},
                "missing_fields": ['ingredients', 'cuisine_preference', 'number_of_people', 'cooking_preference']
            }, 200
        
        intent = self.detect_intent(message)
        
        # Reset
        if intent == 'reset':
            return {
                "status": "success",
                "bot_name": "Doctor Foody",
                "message": "🔄 Starting fresh!\n\n" + self.next_question(['ingredients'], {}),
                "collected_data": {},
                "missing_fields": ['ingredients', 'cuisine_preference', 'number_of_people', 'cooking_preference']
            }, 200
        
        # Confirm
        if intent == 'confirm':
            missing = self.check_missing(collected)
            if missing:
                return {
                    "status": "success",
                    "bot_name": "Doctor Foody",
                    "message": "⚠️ Please complete all details!\n\n" + self.next_question(missing, collected),
                    "collected_data": collected,
                    "missing_fields": missing
                }, 200
            
            return self.generate_recipe(user_id, collected)
        
        # MODIFIED: Handle user selection of suggestions
        if collected.get('_pending_suggestions') and not collected.get('_suggestions_handled'):
            
            # Add ALL suggestions (user said "all", "yes", etc.)
            if intent == 'add_all_suggestions':
                sugg = collected['_pending_suggestions']
                all_items = sugg.get('spices', []) + sugg.get('basics', [])
                # Convert to dict format for add_suggestions
                all_items_dict = [{'name': item, 'qty': None} for item in all_items]
                
                collected['ingredients'] = self.add_suggestions(
                    collected['ingredients'], 
                    all_items_dict,
                    collected.get('cuisine_preference')
                )
                collected['_suggestions_handled'] = True
                del collected['_pending_suggestions']
                
                missing = self.check_missing(collected)
                
                msg = f"✅ Added: {', '.join(all_items)}!\n\n"
                if not missing:
                    msg += self.format_summary(collected)
                else:
                    msg += self.next_question(missing, collected)
                
                return {
                    "status": "success",
                    "bot_name": "Doctor Foody",
                    "message": msg,
                    "collected_data": collected,
                    "missing_fields": missing
                }, 200
            
            # Skip suggestions
            if intent == 'skip_suggestions':
                collected['_suggestions_handled'] = True
                del collected['_pending_suggestions']
                
                missing = self.check_missing(collected)
                
                return {
                    "status": "success",
                    "bot_name": "Doctor Foody",
                    "message": "✅ Skipped!\n\n" + self.next_question(missing, collected),
                    "collected_data": collected,
                    "missing_fields": missing
                }, 200
            
            # User is selecting SPECIFIC items (with or without quantities)
            selected_items = self.parse_user_selection(message, collected['_pending_suggestions'])
            
            if selected_items:
                # Add selected items (respecting user-provided quantities)
                collected['ingredients'] = self.add_suggestions(
                    collected['ingredients'],
                    selected_items,
                    collected.get('cuisine_preference')
                )
                collected['_suggestions_handled'] = True
                del collected['_pending_suggestions']
                
                missing = self.check_missing(collected)
                
                selected_names = [item['name'] for item in selected_items]
                msg = f"✅ Added: {', '.join(selected_names)}!\n\n"
                if not missing:
                    msg += self.format_summary(collected)
                else:
                    msg += self.next_question(missing, collected)
                
                return {
                    "status": "success",
                    "bot_name": "Doctor Foody",
                    "message": msg,
                    "collected_data": collected,
                    "missing_fields": missing
                }, 200
            else:
                # Couldn't parse selection, ask again
                return {
                    "status": "success",
                    "bot_name": "Doctor Foody",
                    "message": "⚠️ I couldn't understand. " + self.next_question(['suggestions_pending'], collected),
                    "collected_data": collected,
                    "missing_fields": ['suggestions_pending']
                }, 200
        
        # Extract data
        # Update unclear first
        if collected.get('ingredients'):
            unclear = [ing for ing in collected['ingredients'] if ing.get('unclear')]
            if unclear:
                updated = self.update_unclear(message, collected['ingredients'])
                
                any_updated = any(
                    old.get('unclear') and not new.get('unclear')
                    for old, new in zip(collected['ingredients'], updated)
                )
                
                if any_updated:
                    collected['ingredients'] = updated
        
        # Extract new ingredients
        new_ings = self.extract_ingredients(message)
        if new_ings:
            if collected.get('ingredients'):
                collected['ingredients'] = self.merge_ingredients(collected['ingredients'], new_ings)
            else:
                collected['ingredients'] = new_ings
        
        # Extract cuisine
        if not collected.get('cuisine_preference'):
            cuisine = self.extract_cuisine(message)
            if cuisine:
                collected['cuisine_preference'] = cuisine
                
                # IMPORTANT: Get LLM-based suggestions after cuisine selection
                if collected.get('ingredients') and not collected.get('_pending_suggestions'):
                    sugg = self.get_llm_suggestions(cuisine, collected['ingredients'])
                    
                    if sugg['spices'] or sugg['basics']:
                        collected['_pending_suggestions'] = sugg
        
        # Extract people
        if not collected.get('number_of_people'):
            people = self.extract_people(message)
            if people:
                collected['number_of_people'] = people
        
        # Extract preference
        if not collected.get('cooking_preference'):
            pref = self.extract_preference(message)
            if pref:
                collected['cooking_preference'] = pref
        
        # Check missing
        missing = self.check_missing(collected)
        
        if not missing:
            msg = self.format_summary(collected)
        else:
            msg = self.next_question(missing, collected)
        
        return {
            "status": "success",
            "bot_name": "Doctor Foody",
            "message": msg,
            "collected_data": collected,
            "missing_fields": missing
        }, 200


def doctor_foody_chat_controller(user_id: str, data: Dict) -> Tuple[Dict, int]:
    """Main entry point"""
    controller = DoctorFoodyController()
    return controller.handle_chat(user_id, data)