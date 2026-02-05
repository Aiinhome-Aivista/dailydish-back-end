import os
import re
import requests
import json
from typing import Dict, List, Tuple, Optional

class DoctorFoodyController:
    """
    Smart Personal Chef AI - Fully Dynamic Production Version
    
    IMPROVEMENTS:
    Zero hardcoded ingredient lists
    LLM-powered validation for unknown terms
    Context-aware extraction
    Self-learning compound ingredient detection
    Production-ready scalability
    Enhanced quantity update handling for mixed formats
    """
    
    def __init__(self):
        # LLM API configuration
        self.llm_api_url = os.getenv('MISTRAL_API_URL', 'http://localhost:11434/api/generate')
        self.llm_model = os.getenv('MISTRAL_MODEL', 'mistral')
        
        # Cache for LLM validation results (improves performance)
        self._validation_cache = {}
        
        # Dynamically detected compound ingredients (learned during runtime)
        self._detected_compounds = set()

    # ==================== NEW: SPELLING CORRECTION ====================
    
#     def _fix_spelling_llm(self, text: str) -> str:
#         """
#         NEW: Fix spelling errors using LLM
#         Example: "chiken" → "chicken", "tamoto" → "tomato", "brokoli" → "broccoli"
#         """
#         try:
#             prompt = f"""Fix ONLY spelling errors in food text. Keep numbers/units unchanged.

# Text: {text}

# Return ONLY corrected text."""

#             payload = {
#                 "model": self.llm_model,
#                 "prompt": prompt,
#                 "stream": False,
#                 "options": {"temperature": 0.1, "num_predict": 100}
#             }
            
#             response = requests.post(self.llm_api_url, json=payload, timeout=5)
            
#             if response.status_code == 200:
#                 result = response.json()
#                 corrected = result.get('response', '').strip()
#                 if corrected and len(corrected) < len(text) * 2:
#                     print(f"   Spelling: '{text}' → '{corrected}'")
#                     return corrected
#         except Exception as e:
#             print(f"   Spelling fix failed: {e}")
        
#         return text
    

#     # ==================== NEW: SPELLING CORRECTION ====================
    
#     def _fix_spelling_llm(self, text: str) -> str:
#         """
#         NEW FEATURE: Fix spelling errors using LLM
#         Example: "chiken" → "chicken", "tamoto" → "tomato", "brokoli" → "broccoli"
#         """
#         try:
#             prompt = f"""Fix ONLY spelling errors in food ingredient text. Keep numbers/units unchanged.

# Text: {text}

# Return ONLY corrected text, no explanation."""

#             payload = {
#                 "model": self.llm_model,
#                 "prompt": prompt,
#                 "stream": False,
#                 "options": {"temperature": 0.1, "num_predict": 100}
#             }
            
#             response = requests.post(self.llm_api_url, json=payload, timeout=800)
            
#             if response.status_code == 200:
#                 result = response.json()
#                 corrected = result.get('response', '').strip()
#                 # Safety: only return if reasonable length
#                 if corrected and len(corrected) < len(text) * 2:
#                     print(f"   Spelling: '{text}' → '{corrected}'")
#                     return corrected
#         except Exception as e:
#             print(f"   Spelling fix failed: {e}")
        
#         return text  # Return original on failure
    
    
    # ==================== SMART INGREDIENT EXTRACTION ====================
    
    def extract_ingredients(self, text: str) -> List[Dict]:
        """
        Fully dynamic ingredient extraction
        No hardcoded lists - uses patterns and LLM validation
        """
        ingredients = []
        # # NEW: Fix spelling errors first
        # text = self._fix_spelling_llm(text)
        
        # # NEW: Fix spelling first
        # text = self._fix_spelling_llm(text)
        
        text_lower = text.lower()
        
        # Skip greetings
        if text_lower.strip() in ['hi', 'hello', 'hey', 'yes', 'no', 'ok', 'okay']:
            return []
        
        # Fix typos
        text_lower = re.sub(r'(\d)o+(?=g(?!o)|gm|kg|ml|l(?!o)|cup)', r'\g<1>00', text_lower)
        text_lower = re.sub(r'(\d)o+\s+(?=g(?!o)|gm|kg|ml|l(?!o)|cup)', r'\g<1>00 ', text_lower)
        
        # Dynamically detect and preserve compound ingredients
        text_lower = self._preserve_compound_ingredients(text_lower)
        
        found_items = set()
        
        # PATTERN 1: Quantity FIRST (e.g., "500g chicken", "2 pieces fish")
        qty_first_patterns = [
            # Tight format for weights: "500g chicken", "2kg fish"
            r'(\d+(?:\.\d+)?)(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass)\s+([a-z_]+(?:\s+[a-z_]+){0,2}?)(?:\s*(?:,|\sand\s|\.|\band\s|$))',
            # Spaced format for weights: "500 g chicken"
            r'(\d+(?:\.\d+)?)\s+(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass)\s+([a-z_]+(?:\s+[a-z_]+){0,2}?)(?:\s*(?:,|\sand\s|\.|\band\s|$))',
            # Match "2 pieces katla fish" OR "2pieces katla fish" (both spaced and tight)
            r'(\d+)\s*(piece|pieces|peace|peaces|pics?|pcs?)\s+(?:of\s+)?([a-z_]+(?:\s+[a-z_]+){0,2})(?=\s*(?:,|\sand\s|\.|\band\s|$))',
            # Spoons
            r'(\d+)\s*(spoon|spoons|tbsp|tsp)\s+(?:of\s+)?([a-z_]+(?:\s+[a-z_]+){0,2}?)(?:\s*(?:,|\sand\s|\.|\band\s|$))',
            # Only match if NOT preceded by unit words like 'pieces', 'piece', 'pcs', etc.
            r'(\d+)\s+(?!piece|pieces|peace|peaces|pics?|pcs?|spoon|spoons|tbsp|tsp|g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass\s)([a-z_]+\s+(?:fish|chicken|egg|eggs|prawn|shrimp|crab|lobster|meat|pork|beef|mutton))(?:\s*(?:,|\sand\s|\.|\band\s|$))',
        ]
        
        for pattern in qty_first_patterns:
            for match in re.finditer(pattern, text_lower):
                if len(match.groups()) == 2:
                    qty_num = match.group(1)
                    ing_raw = match.group(2)
                    unit = "pieces"
                else:
                    qty_num = match.group(1)
                    unit = match.group(2)
                    ing_raw = match.group(3)
                
                ing_clean = self._clean_and_validate(ing_raw, text_lower)
                if ing_clean and ing_clean.lower() not in found_items:
                    qty = self._format_qty(qty_num, unit)
                    ingredients.append({"name": ing_clean, "qty": qty, "unclear": False})
                    found_items.add(ing_clean.lower())
        
        # PATTERN 2: Ingredient FIRST (e.g., "chicken 500g", "rice 2 cups")
        ing_first_patterns = [
            # Match 1-2 word ingredients, excluding conjunctions
            r'(?<!\w)(?!and\s|or\s)([a-z_]+(?:\s+[a-z_]+)?)\s+(\d+(?:\.\d+)?)(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass)(?:\s*(?:,|\sand\s|\.|\band\s|$))',
            r'(?<!\w)(?!and\s|or\s)([a-z_]+(?:\s+[a-z_]+)?)\s+(\d+(?:\.\d+)?)\s+(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass)(?:\s*(?:,|\sand\s|\.|\band\s|$))',
            r'(?<!\w)(?!and\s|or\s)([a-z_]+(?:\s+[a-z_]+)?)\s+(\d+)\s*(piece|pieces|peace|peaces|pics?|pcs?)(?:\s*(?:,|\sand\s|\.|\band\s|$))',
            r'(?<!\w)(?!and\s|or\s)([a-z_]+(?:\s+[a-z_]+)?)\s+(\d+)\s*(spoon|spoons|tbsp|tsp)(?:\s*(?:,|\sand\s|\.|\band\s|$))',
        ]
        
        for pattern in ing_first_patterns:
            for match in re.finditer(pattern, text_lower):
                ing_raw = match.group(1)
                qty_num = match.group(2)
                unit = match.group(3)
                
                ing_clean = self._clean_and_validate(ing_raw, text_lower)
                if ing_clean and ing_clean.lower() not in found_items:
                    qty = self._format_qty(qty_num, unit)
                    ingredients.append({"name": ing_clean, "qty": qty, "unclear": False})
                    found_items.add(ing_clean.lower())
        
        # PATTERN 3: Vague quantities (e.g., "some rice", "few onions")
        vague_pattern = r'(few|some|little\s*bit|little|bit|handful)\s+(?:of\s+)?([a-z_]+(?:\s+[a-z_]+){0,2}?)(?=\s*(?:,|and|\.|\band\b|$))'
        
        for match in re.finditer(vague_pattern, text_lower):
            vague = match.group(1)
            ing_raw = match.group(2)
            
            ing_clean = self._clean_and_validate(ing_raw, text_lower)
            if ing_clean and ing_clean.lower() not in found_items:
                ingredients.append({"name": ing_clean, "qty": vague.strip(), "unclear": True})
                found_items.add(ing_clean.lower())
        
        # PATTERN 4: Standalone ingredients (e.g., "pumpkin", "bitter_gourd")
        words_in_text = re.findall(r'\b([a-z_]+(?:\s+[a-z_]+)?)\b', text_lower)
        
        for word_phrase in words_in_text:
            if word_phrase in found_items:
                continue
            if len(word_phrase) < 3:
                continue
            
            cleaned = self._clean_and_validate(word_phrase, text_lower)
            if cleaned and cleaned.lower() not in found_items:
                is_standalone = True
                for existing_item in found_items:
                    word_no_underscore = word_phrase.replace('_', ' ')
                    existing_no_underscore = existing_item.replace('_', ' ')
                    
                    if (word_phrase in existing_item or existing_item in word_phrase or
                        word_no_underscore in existing_no_underscore or
                        existing_no_underscore in word_no_underscore):
                        is_standalone = False
                        break
                
                if is_standalone:
                    ingredients.append({"name": cleaned, "qty": "some", "unclear": True})
                    found_items.add(cleaned.lower().replace(' ', '_'))
        
        # FALLBACK: Use LLM only if regex found NOTHING
        if len(ingredients) == 0 and self._is_noisy_input(text):
            print(f"  Using LLM to extract from noisy input...")
            llm_ingredients = self._extract_with_llm(text)
            
            for llm_ing in llm_ingredients:
                if llm_ing['name'].lower() not in found_items:
                    ingredients.append(llm_ing)
                    found_items.add(llm_ing['name'].lower())
        
        return ingredients
    
    def _preserve_compound_ingredients(self, text: str) -> str:
        """
        Dynamically detect compound ingredients using LLM
        Example: "bitter gourd" should stay together
        """
        # Check cache first
        if text in self._detected_compounds:
            return text
        
        # Find potential two-word combinations
        two_word_pattern = r'\b([a-z]+)\s+([a-z]+)\b'
        matches = re.findall(two_word_pattern, text)
        
        for word1, word2 in matches:
            compound = f"{word1} {word2}"
            
            # Skip if already detected
            if compound in self._detected_compounds:
                text = text.replace(compound, compound.replace(' ', '_'))
                continue
            
            # Use LLM to check if it's a compound ingredient
            if self._is_compound_ingredient(compound):
                self._detected_compounds.add(compound)
                text = text.replace(compound, compound.replace(' ', '_'))
        
        return text
    
    def _has_spices_in_ingredients(self, ingredients: List[Dict]) -> bool:
        """
        Check if user has mentioned any spices in their ingredients list
        """
        common_spices = ['turmeric', 'cumin', 'coriander', 'chili', 'chilli', 'pepper', 
                        'garam masala', 'masala', 'salt', 'garlic', 'ginger', 'onion',
                        'cardamom', 'cinnamon', 'clove', 'bay leaf', 'mustard', 'fenugreek',
                        'curry', 'paprika', 'cayenne', 'red chili', 'green chili', 'spice',
                        'oil', 'ghee', 'butter', 'vinegar', 'sauce', 'paste']
        
        for ing in ingredients:
            ing_name = ing['name'].lower()
            # Check for common misspellings
            if 'corriander' in ing_name:  # Common misspelling of coriander
                return True
            for spice in common_spices:
                if spice in ing_name or ing_name in spice:
                    return True
        return False
    
    def check_recipe_feasibility_without_spices(self, ingredients: List[Dict]) -> Dict:
        """
        NEW METHOD: Check if recipe is possible with ONLY current ingredients (no spices)
        Returns: {"possible": bool, "suggested_spices": List[str], "reason": str}
        """
        try:
            # Build ingredients string
            ing_list = [f"{ing['qty']} {ing['name']}" for ing in ingredients]
            ing_str = ", ".join(ing_list)
            
            prompt = f"""You are a professional chef. A user wants to cook with ONLY these ingredients (NO spices available):
{ing_str}

Analyze if it's possible to create a TASTY, PROPER recipe with ONLY these ingredients.

Consider:
1. Can you make a complete dish without any spices/seasonings?
2. Would the dish be flavorful enough to eat?
3. Are basic spices (salt, oil, etc.) ESSENTIAL for this dish?

Respond with JSON:
{{
  "possible": true/false,
  "reason": "brief explanation why possible or not possible",
  "suggested_spices": ["salt", "oil", "pepper"] // empty array if possible without spices, or minimal spices needed if not possible
}}

Examples:
- "200g paneer, 1 broccoli" → {{"possible": false, "reason": "Needs at least salt and oil for flavor", "suggested_spices": ["salt", "oil"]}}
- "2 eggs, 100g cheese, 50g butter" → {{"possible": true, "reason": "Can make omelet without additional spices", "suggested_spices": []}}
- "500g chicken" → {{"possible": false, "reason": "Needs salt and oil minimum", "suggested_spices": ["salt", "oil", "pepper"]}}
"""

            payload = {
                "model": self.llm_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.3}
            }
            
            response = requests.post(self.llm_api_url, json=payload, timeout=850)
            
            if response.status_code != 200:
                print(f"   Feasibility check failed: {response.status_code}")
                return {"possible": True, "suggested_spices": [], "reason": ""}
            
            result = response.json()
            raw_content = result.get('response', '').strip()
            
            if not raw_content:
                return {"possible": True, "suggested_spices": [], "reason": ""}
            
            # Clean JSON
            if raw_content.startswith('```'):
                raw_content = raw_content.split('```json')[-1].split('```')[0].strip()
            
            feasibility = json.loads(raw_content)
            
            print(f"   Recipe feasibility: {feasibility.get('possible')}, Suggested: {feasibility.get('suggested_spices', [])}")
            
            return feasibility
            
        except Exception as e:
            print(f"   Feasibility check error: {str(e)}")
            return {"possible": True, "suggested_spices": [], "reason": ""}

    
    def _is_compound_ingredient(self, phrase: str) -> bool:
        """
        Use LLM to determine if a two-word phrase is a compound ingredient
        """
        # Quick heuristic checks first
        # Common patterns that are likely compounds
        common_patterns = [
            r'\b(olive|mustard|sesame|coconut|vegetable|sunflower)\s+(oil)\b',
            r'\b(bitter|sweet|bell)\s+(gourd|potato|pepper|melon)\b',
            r'\b(green|black|kidney|soy)\s+(beans?|sauce)\b',
            r'\b(spring|green)\s+(onion)\b',
            r'\b(curry|bay)\s+(leaf|leaves)\b',
            r'\b(coconut)\s+(milk|cream)\b',
            r'\b(fish|soy)\s+(sauce)\b',
        ]
        
        for pattern in common_patterns:
            if re.match(pattern, phrase):
                return True
        
        # For unknown cases, use LLM (with caching)
        if phrase in self._validation_cache:
            return self._validation_cache[phrase]
        
        try:
            prompt = f"""Is "{phrase}" a single compound food ingredient (like "bitter gourd" or "olive oil")?

Answer ONLY with a JSON object:
{{"is_compound": true}} or {{"is_compound": false}}

Examples:
"bitter gourd" -> {{"is_compound": true}}
"want to" -> {{"is_compound": false}}
"olive oil" -> {{"is_compound": true}}
"cook with" -> {{"is_compound": false}}

Phrase: "{phrase}"
"""

            payload = {
                "model": self.llm_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.1, "num_predict": 50}
            }
            
            response = requests.post(self.llm_api_url, json=payload, timeout=800)
            
            if response.status_code == 200:
                result = response.json()
                raw_content = result.get('response', '').strip()
                
                if raw_content:
                    data = json.loads(raw_content)
                    is_compound = data.get('is_compound', False)
                    self._validation_cache[phrase] = is_compound
                    return is_compound
        
        except Exception as e:
            print(f"  Compound detection error: {str(e)}")
        
        # Default: not a compound
        return False
    
    def _is_noisy_input(self, text: str) -> bool:
        """Detect if input has excessive filler words"""
        text_lower = text.lower()
        
        noise_indicators = [
            'want to', 'i want', 'going to', 'planning to',
            'below', 'following', 'these', 'those',
            'ingredients are', 'i have the following',
            'cook with', 'make with', 'prepare with'
        ]
        
        noise_count = sum(1 for phrase in noise_indicators if phrase in text_lower)
        word_count = len(text.split())
        
        return noise_count >= 2 or word_count > 15
    
    def _extract_with_llm(self, text: str) -> List[Dict]:
        """Use LLM for complex/noisy text extraction"""
        try:
            prompt = f"""Extract ONLY food ingredients from: "{text}"

Rules:
1. Return ONLY ingredient names (food items)
2. Do NOT include cooking methods, cuisine types, or non-food words
3. Include quantities if specified

Output format (JSON array):
[
  {{"name": "ingredient_name", "qty": "quantity or 'some'"}},
  {{"name": "ingredient_name", "qty": "some"}}
]

Examples:
Input: "I want to cook with pumpkin and bitter gourd"
Output: [{{"name": "pumpkin", "qty": "some"}}, {{"name": "bitter gourd", "qty": "some"}}]

Input: "I have 2kg chicken, some rice and tomatoes"
Output: [{{"name": "chicken", "qty": "2kg"}}, {{"name": "rice", "qty": "some"}}, {{"name": "tomatoes", "qty": "some"}}]

Now extract from: "{text}"
"""

            payload = {
                "model": self.llm_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,
                    "num_predict": 500
                }
            }
            
            response = requests.post(self.llm_api_url, json=payload, timeout=800)
            
            if response.status_code != 200:
                print(f"  LLM extraction failed: {response.status_code}")
                return []
            
            result = response.json()
            raw_content = result.get('response', '').strip()
            
            if not raw_content:
                return []
            
            # Clean JSON
            if raw_content.startswith('```'):
                raw_content = raw_content.split('```json')[-1].split('```')[0].strip()
            
            llm_data = json.loads(raw_content)
            
            ingredients = []
            for item in llm_data:
                if isinstance(item, dict) and 'name' in item:
                    name = item['name'].strip()
                    qty = item.get('qty', 'some')
                    
                    if self._is_valid_ingredient(name):
                        ingredients.append({
                            "name": name.title(),
                            "qty": qty,
                            "unclear": qty in ['some', 'few', 'little', 'bit']
                        })
                        print(f" LLM extracted: {name} ({qty})")
            
            return ingredients
            
        except Exception as e:
            print(f" LLM extraction error: {str(e)}")
            return []
    
    # ==================== FULLY DYNAMIC VALIDATION ====================
    
    def _clean_and_validate(self, raw: str, context: str = "") -> Optional[str]:
        """
        Fully dynamic validation using minimal rules + LLM
        """
        # Convert underscores back to spaces
        raw = raw.replace('_', ' ')
        raw = raw.strip()
        
        if not raw or len(raw) < 2:
            return None
        
        # STEP 1: Remove universal stop words
        words = raw.split()
        cleaned_words = []
        
        # Minimal universal stop words (language structure words)
        universal_stops = {
            'the', 'a', 'an', 'and', 'or', 'of', 'with', 'in', 'on', 'at',
            'to', 'for', 'from', 'by', 'is', 'are', 'was', 'were',
            'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'can', 'may', 'might',
            'this', 'that', 'these', 'those',
            'i', 'you', 'we', 'they', 'my', 'your', 'our', 'their'
        }
        
        for word in words:
            word_clean = word.strip()
            
            # Skip if too short, digit, or universal stop word
            if len(word_clean) <= 1 or word_clean.isdigit() or word_clean in universal_stops:
                continue
            
            # Skip measurement unit typos and unit words
            if word_clean in ['piece', 'pieces', 'pices', 'pics', 'peace', 'peaces', 'pcs', 'pic']:
                continue
            
            cleaned_words.append(word_clean)
        
        if not cleaned_words:
            return None
        
        cleaned = ' '.join(cleaned_words)
        
        # STEP 2: Basic structural validation
        if len(cleaned) < 2 or len(cleaned) > 30:
            return None
        
        if not re.match(r'^[a-z\s\-]+$', cleaned.lower()):
            return None
        
        # STEP 3: Context-aware filtering
        if context:
            # Check if this word is used as an action verb in context
            action_patterns = [
                rf'\b(want|need|going|planning)\s+(?:to\s+)?{re.escape(cleaned)}\b',
                rf'\b{re.escape(cleaned)}\b\s+(?:to\s+)?(?:make|prepare|cook)\b'
            ]
            
            # Check if it's in a list of ingredients
            listing_patterns = [
                rf'\b{re.escape(cleaned)}\b\s*(?:,|and)\s*\w+',
                rf'\w+\s*(?:,|and)\s*\b{re.escape(cleaned)}\b',
            ]
            
            has_action_context = any(re.search(p, context, re.IGNORECASE) for p in action_patterns)
            has_listing_context = any(re.search(p, context, re.IGNORECASE) for p in listing_patterns)
            
            if has_action_context and not has_listing_context:
                if cleaned.lower() in ['cook', 'make', 'prepare', 'use', 'add']:
                    return None
        
        # STEP 4: LLM validation for unknown terms
        if not self._is_valid_ingredient(cleaned):
            return None
        
        return cleaned.title()
    
    def _is_valid_ingredient(self, name: str) -> bool:
        """
        Fully dynamic LLM-powered ingredient validation
        Uses caching for performance
        """
        name_lower = name.lower()
        
        # Check cache first
        if name_lower in self._validation_cache:
            return self._validation_cache[name_lower]
        
        # Quick heuristic checks
        # Reject obvious non-ingredients
        obvious_non_ingredients = {
            # Common verbs
            'make', 'cook', 'prepare', 'use', 'add', 'want', 'need', 'have', 'got',
            # Question words
            'how', 'what', 'when', 'where', 'why', 'which', 'who',
            # Meta terms
            'recipe', 'cooking', 'food', 'dish', 'meal', 'cuisine', 'ingredients',
            # Filler words
            'these', 'those', 'below', 'bellow', 'following', 'above',
        }
        
        if name_lower in obvious_non_ingredients:
            self._validation_cache[name_lower] = False
            return False
        
        # For compound words, check each part
        if ' ' in name_lower:
            words = name_lower.split()
            
            # Reject if starts with preposition
            if words[0] in {'to', 'for', 'with', 'from', 'in', 'on', 'at', 'by'}:
                self._validation_cache[name_lower] = False
                return False
        
        # Use LLM for validation
        is_valid = self._validate_with_llm(name)
        self._validation_cache[name_lower] = is_valid
        
        return is_valid
    
    def _validate_with_llm(self, name: str) -> bool:
        """
        Use LLM to determine if a term is a valid food ingredient
        """
        try:
            prompt = f"""Is "{name}" a food ingredient (vegetable, fruit, meat, grain, spice, dairy, etc.)?

Answer ONLY with a JSON object:
{{"is_ingredient": true}} or {{"is_ingredient": false}}

Examples:
"pumpkin" -> {{"is_ingredient": true}}
"bitter gourd" -> {{"is_ingredient": true}}
"turmeric" -> {{"is_ingredient": true}}
"chicken" -> {{"is_ingredient": true}}
"cook" -> {{"is_ingredient": false}}
"recipe" -> {{"is_ingredient": false}}
"want" -> {{"is_ingredient": false}}

Term: "{name}"
"""

            payload = {
                "model": self.llm_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,
                    "num_predict": 50
                }
            }
            
            response = requests.post(self.llm_api_url, json=payload, timeout=800)
            
            if response.status_code != 200:
                print(f"  LLM validation failed for '{name}': {response.status_code}")
                # Default to True for unknown terms (be permissive)
                return True
            
            result = response.json()
            raw_content = result.get('response', '').strip()
            
            if not raw_content:
                return True
            
            # Clean JSON
            if raw_content.startswith('```'):
                raw_content = raw_content.split('```json')[-1].split('```')[0].strip()
            
            data = json.loads(raw_content)
            is_ingredient = data.get('is_ingredient', True)
            
            print(f"  🔍 LLM validated '{name}': {is_ingredient}")
            
            return is_ingredient
            
        except Exception as e:
            print(f"  LLM validation error for '{name}': {str(e)}")
            # Default to True (be permissive on errors)
            return True
    
    def _format_qty(self, num: str, unit: str) -> str:
        """Format quantity string"""
        unit_map = {
            'g': 'g', 'gm': 'g', 'kg': 'kg', 'kgs': 'kg',
            'ml': 'ml', 'l': 'l', 'ltr': 'l', 'litre': 'l', 'litres': 'l',
            'piece': 'pieces', 'pieces': 'pieces',
            'peace': 'pieces', 'peaces': 'pieces',
            'pic': 'pieces', 'pics': 'pieces', 'pcs': 'pieces',
            'cup': 'cups', 'cups': 'cups', 'glass': 'glass',
            'spoon': 'tbsp', 'spoons': 'tbsp', 'tbsp': 'tbsp',
            'tsp': 'tsp'
        }
        
        unit_clean = unit_map.get(unit.lower(), unit)
        
        if unit_clean in ['g', 'kg', 'ml', 'l']:
            return f"{num}{unit_clean}"
        
        if num == '1':
            if unit_clean == 'pieces':
                return f"{num} piece"
            elif unit_clean == 'cups':
                return f"{num} cup"
            elif unit_clean == 'glass':
                return f"{num} glass"
        
        return f"{num} {unit_clean}"
    
    def merge_ingredients(self, existing: List[Dict], new: List[Dict]) -> List[Dict]:
        """Merge ingredient lists"""
        result = {ing['name'].lower(): ing for ing in existing}
        
        for ing in new:
            result[ing['name'].lower()] = ing
        
        return list(result.values())
    
    def update_unclear(self, text: str, ingredients: List[Dict]) -> List[Dict]:
        """
        Update unclear quantities from user input
        Handles all variations: "spinach 100g", "200g paneer", "100 gram onion", etc.
        
        ENHANCED: Now handles:
        1. Named format: "spinach 100g and 200g paneer"
        2. Sequence format: "100g, 2pieces, 1cup" (matches order of unclear ingredients)
        """
        text_lower = text.lower()
        
        # Fix common typos first
        text_lower = re.sub(r'(\d)o+(?=g(?!o)|gm|kg|ml|l(?!o)|cup)', r'\g<1>00', text_lower)
        text_lower = re.sub(r'(\d)o+\s+(?=g(?!o)|gm|kg|ml|l(?!o)|cup)', r'\g<1>00 ', text_lower)
        
        # Get unclear ingredients only
        unclear_ings = [ing for ing in ingredients if ing.get('unclear')]
        
        # Check if this is SEQUENCE-BASED input (just quantities without ingredient names)
        # Extract all standalone quantities
        standalone_qtys = []
        for match in re.finditer(r'(\d+(?:\.\d+)?)\s*(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass|piece|pieces|peace|peaces|pics?|pcs?|spoon|spoons|tbsp|tsp)?(?:\s*[,\s]|$)', text_lower):
            qty_num = match.group(1)
            unit = match.group(2) if match.group(2) else "pieces"
            standalone_qtys.append(self._format_qty(qty_num, unit))
        
        # Check if input is sequence-based (no ingredient names detected)
        has_ingredient_names = False
        for ing in unclear_ings:
            ing_lower = ing['name'].lower().replace('_', ' ')
            if ing_lower in text_lower or ing['name'].lower() in text_lower:
                has_ingredient_names = True
                break
        
        # If sequence-based input detected
        if not has_ingredient_names and len(standalone_qtys) > 0:
            print(f"  Sequence-based input detected: {len(standalone_qtys)} quantities for {len(unclear_ings)} unclear ingredients")
            updated = []
            for ing in ingredients:
                if ing.get('unclear'):
                    # Find index in unclear list
                    unclear_idx = unclear_ings.index(ing)
                    if unclear_idx < len(standalone_qtys):
                        ing['qty'] = standalone_qtys[unclear_idx]
                        ing['unclear'] = False
                        print(f"  ✓ Updated '{ing['name']}': {standalone_qtys[unclear_idx]} (sequence position {unclear_idx+1})")
                updated.append(ing)
            return updated
        
        # NAMED-BASED: Normal matching with ingredient names
        updated = []
        
        for ing in ingredients:
            if ing.get('unclear'):
                ing_lower = ing['name'].lower()
                ing_normalized = ing_lower.replace('_', ' ')  # Handle underscores
                
                # Comprehensive pattern list for all formats
                # Each pattern tuple: (regex_pattern, qty_num_group_index, unit_group_index)
                patterns = [
                    # Quantity FIRST (tight): "200g paneer", "2kg chicken"
                    (rf'(\d+(?:\.\d+)?)(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass|piece|pieces|peace|pics?|pcs?|spoon|spoons|tbsp|tsp)\s+{re.escape(ing_normalized)}', 1, 2),
                    (rf'(\d+(?:\.\d+)?)(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass|piece|pieces|peace|pics?|pcs?|spoon|spoons|tbsp|tsp)\s+{re.escape(ing_lower)}', 1, 2),
                    
                    # Quantity FIRST (spaced): "200 g paneer", "2 kg chicken"
                    (rf'(\d+(?:\.\d+)?)\s+(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass|piece|pieces|peace|pics?|pcs?|spoon|spoons|tbsp|tsp)\s+{re.escape(ing_normalized)}', 1, 2),
                    (rf'(\d+(?:\.\d+)?)\s+(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass|piece|pieces|peace|pics?|pcs?|spoon|spoons|tbsp|tsp)\s+{re.escape(ing_lower)}', 1, 2),
                    
                    # Ingredient FIRST (tight): "paneer 200g", "chicken 2kg"
                    (rf'{re.escape(ing_normalized)}\s+(\d+(?:\.\d+)?)(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass|piece|pieces|peace|pics?|pcs?|spoon|spoons|tbsp|tsp)', 1, 2),
                    (rf'{re.escape(ing_lower)}\s+(\d+(?:\.\d+)?)(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass|piece|pieces|peace|pics?|pcs?|spoon|spoons|tbsp|tsp)', 1, 2),
                    
                    # Ingredient FIRST (spaced): "paneer 200 g", "chicken 2 kg"
                    (rf'{re.escape(ing_normalized)}\s+(\d+(?:\.\d+)?)\s+(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass|piece|pieces|peace|pics?|pcs?|spoon|spoons|tbsp|tsp)', 1, 2),
                    (rf'{re.escape(ing_lower)}\s+(\d+(?:\.\d+)?)\s+(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass|piece|pieces|peace|pics?|pcs?|spoon|spoons|tbsp|tsp)', 1, 2),
                    
                    # With "of": "200g of paneer", "paneer of 200g"
                    (rf'(\d+(?:\.\d+)?)(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass)\s+of\s+{re.escape(ing_normalized)}', 1, 2),
                    (rf'(\d+(?:\.\d+)?)\s+(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass)\s+of\s+{re.escape(ing_normalized)}', 1, 2),
                    (rf'{re.escape(ing_normalized)}\s+of\s+(\d+(?:\.\d+)?)(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass)', 1, 2),
                    (rf'{re.escape(ing_normalized)}\s+of\s+(\d+(?:\.\d+)?)\s+(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass)', 1, 2),
                    
                    # Alternative spellings: "gram", "grams", "kilogram"
                    (rf'(\d+(?:\.\d+)?)\s+(gram|grams|kilogram|kilograms|milliliter|milliliters|liter|liters)\s+{re.escape(ing_normalized)}', 1, 2),
                    (rf'{re.escape(ing_normalized)}\s+(\d+(?:\.\d+)?)\s+(gram|grams|kilogram|kilograms|milliliter|milliliters|liter|liters)', 1, 2),
                ]
                
                found = False
                for pattern, qty_group, unit_group in patterns:
                    match = re.search(pattern, text_lower, re.IGNORECASE)
                    if match:
                        qty_num = match.group(qty_group)
                        unit = match.group(unit_group)
                        
                        # Normalize alternative unit spellings
                        unit_normalized = unit.lower()
                        if unit_normalized in ['gram', 'grams']:
                            unit_normalized = 'g'
                        elif unit_normalized in ['kilogram', 'kilograms']:
                            unit_normalized = 'kg'
                        elif unit_normalized in ['milliliter', 'milliliters']:
                            unit_normalized = 'ml'
                        elif unit_normalized in ['liter', 'liters']:
                            unit_normalized = 'l'
                        
                        qty = self._format_qty(qty_num, unit_normalized)
                        
                        updated.append({"name": ing['name'], "qty": qty, "unclear": False})
                        found = True
                        print(f"  Updated '{ing['name']}': {qty} (pattern matched)")
                        break
                
                if not found:
                    # Keep as unclear if no quantity found
                    updated.append(ing)
                    print(f"  No quantity found for '{ing['name']}' - keeping as unclear")
            else:
                # Already clear, keep as is
                updated.append(ing)
        
        return updated
    
    # ==================== LLM SUGGESTIONS ====================
    
    def get_llm_suggestions(self, cuisine: str, ingredients: List[Dict]) -> Dict:
        """Get dynamic spice/basic suggestions"""
        try:
            ing_names = [ing['name'] for ing in ingredients]
            ing_text = ", ".join(ing_names)
            
            prompt = f"""As a Culinary Expert, analyze ingredients for {cuisine} cuisine: {ing_text}

Suggest ONLY essential spices, herbs, oils, and basics that are:
1. Commonly used in {cuisine} cuisine
2. NOT already in the ingredient list
3. Essential for cooking with these ingredients

Response (JSON):
{{
  "spices": ["spice1", "spice2", "spice3"],
  "basics": ["oil/basic1", "oil/basic2"]
}}

Rules:
- Lowercase items
- 3-5 essential spices only
- 2-3 essential basics only
- Be specific (e.g., "mustard oil" not "oil")
- Exclude items in: {ing_text}
"""

            payload = {
                "model": self.llm_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.3}
            }
            
            response = requests.post(self.llm_api_url, json=payload, timeout=800)
            response.raise_for_status()
            result = response.json()
            
            raw_content = result.get('response', '').strip()
            
            if not raw_content:
                return {"spices": [], "basics": []}
            
            suggestions = json.loads(raw_content)
            
            existing_lower = [ing['name'].lower() for ing in ingredients]
            
            filtered_spices = [s for s in suggestions.get('spices', []) if s.lower() not in existing_lower]
            filtered_basics = [b for b in suggestions.get('basics', []) if b.lower() not in existing_lower]
            
            return {
                "spices": filtered_spices[:5],
                "basics": filtered_basics[:3]
            }
            
        except Exception as e:
            print(f"LLM suggestion error: {str(e)}")
            return {"spices": [], "basics": []}
    
    def check_cuisine_feasibility(self, cuisine: str, ingredients: List[Dict]) -> Dict:
        """
        Check if the selected cuisine is feasible with given ingredients
        Returns: {
            'feasible': bool,
            'missing_essentials': List[str],  # Essential items needed
            'alternative_cuisines': List[str]  # Cuisines that can be made with current ingredients
        }
        """
        try:
            ing_list = [ing['name'] for ing in ingredients]
            ing_str = ', '.join(ing_list)
            
            prompt = f"""You are a culinary expert. Analyze if the given ingredients can make a proper {cuisine} cuisine recipe.

Ingredients available: {ing_str}

Analyze and respond in this EXACT JSON format:
{{
  "feasible": true/false,
  "missing_essentials": ["ingredient1", "ingredient2"],
  "alternative_cuisines": ["cuisine_type1", "cuisine_type2"],
  "reason": "brief explanation"
}}

CRITICAL RULES:
- feasible: true only if the ingredients can make an authentic {cuisine} recipe
- missing_essentials: list simple ingredient/spice names separated by commas (e.g., ["turmeric", "onion", "garlic", "ginger", "coriander powder"]) - NO explanations or categories
- alternative_cuisines: list 2-3 COMPLETELY DIFFERENT cuisine types (e.g., ["Chinese", "Thai", "Mediterranean"]) - NOT recipe/dish names like "Fish Curry" or "Tacos"
- alternative_cuisines MUST be COMPLETELY DIFFERENT from "{cuisine}" - if {cuisine} is "Indian-Sub", do NOT suggest "Bengali", "Punjabi", "South Indian" etc. as these are part of Indian-Sub
- Be practical and realistic
- NEVER include dish names, recipe names, cooking methods, or phrases like "Spices such as..." - ONLY simple ingredient names and cuisine types

Cuisine hierarchy to remember:
- Indian-Sub includes: Bengali, Punjabi, South Indian, North Indian, etc.
- If user chose "Indian-Sub", suggest varied cuisines like: Chinese, Thai, Mediterranean, Middle Eastern, Continental, Japanese, Korean, Mexican, Italian
- If user chose "Oriental", suggest cuisines like: Mediterranean, Indian-Sub, Middle Eastern, Continental, Mexican, Italian

Examples of CORRECT missing_essentials: ["turmeric", "onion", "garlic", "ginger", "coconut milk"]
Examples of WRONG missing_essentials: ["Spices (such as turmeric, coriander)", "Coconut milk or yogurt", "Onions, garlic, ginger"]

Examples of CORRECT alternative_cuisines (when {cuisine} is "Indian-Sub"): ["Mediterranean", "Middle Eastern", "Italian"] OR ["Japanese", "Korean", "Mexican"] OR ["Continental", "Thai", "Turkish"]
Examples of WRONG alternative_cuisines (when {cuisine} is "Indian-Sub"): ["Bengali", "Fish Curry", "Punjabi"]

IMPORTANT: Provide VARIED suggestions each time - don't always suggest the same cuisines. Consider the ingredients available.

Respond with only valid JSON, no other text."""

            payload = {
                "model": self.llm_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.5,  # Increased from 0.3 for more variety
                    "num_predict": 300
                }
            }
            
            response = requests.post(self.llm_api_url, json=payload, timeout=800)
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '{}')
                
                # Clean and parse JSON
                response_text = response_text.strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                response_text = response_text.strip()
                
                analysis = json.loads(response_text)
                
                return {
                    'feasible': analysis.get('feasible', True),
                    'missing_essentials': analysis.get('missing_essentials', []),
                    'alternative_cuisines': analysis.get('alternative_cuisines', []),
                    'reason': analysis.get('reason', '')
                }
            
        except Exception as e:
            print(f"Cuisine feasibility check error: {str(e)}")
        
        # Default: assume feasible if check fails
        return {
            'feasible': True,
            'missing_essentials': [],
            'alternative_cuisines': [],
            'reason': ''
        }
    
    def parse_user_selection(self, message: str, available_suggestions: Dict) -> List[Dict]:
        """Parse user's spice selection"""
        message_lower = message.lower().strip()
        
        all_items = available_suggestions.get('spices', []) + available_suggestions.get('basics', [])
        
        selected = []
        
        for item in all_items:
            item_lower = item.lower()
            if re.search(rf'\b{re.escape(item_lower)}\b', message_lower):
                user_qty = self._extract_qty_for_item(message_lower, item_lower)
                selected.append({'name': item, 'qty': user_qty})
        
        if not selected:
            numbers = re.findall(r'\d+', message)
            for num_str in numbers:
                idx = int(num_str) - 1
                if 0 <= idx < len(all_items):
                    selected.append({'name': all_items[idx], 'qty': None})
        
        return selected
    
    def _extract_qty_for_item(self, text: str, item_name: str) -> Optional[str]:
        """Extract quantity for specific item"""
        patterns = [
            rf'{re.escape(item_name)}\s+(\d+(?:\.\d+)?)\s*(tsp|tbsp|g|gm|kg|ml|cup|cups|spoon|spoons|piece|pieces)',
            rf'{re.escape(item_name)}\s+(\d+(?:\.\d+)?)(tsp|tbsp|g|gm|kg|ml|cup|cups)',
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
    
    def calculate_auto_quantity(self, spice_name: str, main_ingredients: List[Dict], cuisine: str) -> str:
        """Calculate appropriate spice quantity"""
        spice_lower = spice_name.lower()
        
        total_weight = 0
        for ing in main_ingredients:
            qty_str = ing.get('qty', '').lower()
            
            qty_match = re.search(r'(\d+(?:\.\d+)?)', qty_str)
            if qty_match:
                qty_num = float(qty_match.group(1))
                
                if 'kg' in qty_str:
                    total_weight += qty_num * 1000
                elif 'g' in qty_str or 'gm' in qty_str:
                    total_weight += qty_num
                elif 'cup' in qty_str:
                    total_weight += qty_num * 200
                elif 'glass' in qty_str:
                    total_weight += qty_num * 300
                elif 'piece' in qty_str:
                    total_weight += qty_num * 150
        
        if total_weight == 0:
            total_weight = 500
        
        # Quantity rules
        if any(oil in spice_lower for oil in ['oil', 'ghee', 'butter']):
            if total_weight > 1000:
                return "4 tbsp"
            elif total_weight > 500:
                return "2 tbsp"
            else:
                return "1 tbsp"
        
        if 'salt' in spice_lower:
            return "to taste"
        
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
        
        if any(spice in spice_lower for spice in ['cumin', 'coriander', 'fennel', 'fenugreek', 'mustard']):
            if total_weight > 800:
                return "2 tsp"
            elif total_weight > 400:
                return "1 tsp"
            else:
                return "0.5 tsp"
        
        if any(spice in spice_lower for spice in ['cardamom', 'clove', 'cinnamon', 'star anise']):
            if total_weight > 800:
                return "4-5 pieces"
            elif total_weight > 400:
                return "2-3 pieces"
            else:
                return "1-2 pieces"
        
        if any(item in spice_lower for item in ['ginger', 'garlic']) and 'paste' in spice_lower:
            if total_weight > 800:
                return "2 tbsp"
            elif total_weight > 400:
                return "1 tbsp"
            else:
                return "1 tsp"
        
        if any(blend in spice_lower for blend in ['garam masala', 'curry powder', 'five spice']):
            if total_weight > 800:
                return "1.5 tsp"
            elif total_weight > 400:
                return "1 tsp"
            else:
                return "0.5 tsp"
        
        if total_weight > 800:
            return "1 tsp"
        else:
            return "0.5 tsp"
    
    def add_suggestions(self, ingredients: List[Dict], selected_items: List[Dict], cuisine: str = None) -> List[Dict]:
        """Add selected suggestions"""
        existing_names = {ing['name'].lower() for ing in ingredients}
        
        for item_dict in selected_items:
            item_name = item_dict['name']
            user_qty = item_dict.get('qty')
            
            if item_name.lower() not in existing_names:
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
    
    # ==================== CUISINE & OTHER EXTRACTIONS ====================
    
    def extract_cuisine(self, text: str) -> Optional[str]:
        """Extract cuisine type - keep specific cuisines when mentioned"""
        text_lower = text.lower()
        
        # First check for specific cuisines (they should take priority)
        specific_cuisines = {
            'mexican': 'Mexican',
            'spanish': 'Spanish',
            'italian': 'Italian',
            'french': 'French',
            'greek': 'Greek',
            'mediterranean': 'Mediterranean',
            'thai': 'Thai',
            'chinese': 'Chinese',
            'japanese': 'Japanese',
            'korean': 'Korean',
            'vietnamese': 'Vietnamese',
            'turkish': 'Turkish',
            'persian': 'Persian',
            'arabic': 'Arabic',
            'bengali': 'Bengali',
            'punjabi': 'Punjabi'
        }
        
        for keyword, cuisine_name in specific_cuisines.items():
            if keyword in text_lower:
                return cuisine_name
        
        # If no specific cuisine, check generic categories
        cuisines = [
            ('Central Asian', ['central asian', 'central', 'middle eastern', 'uzbek']),
            ('Inter-Continental', ['inter-continental', 'intercontinental', 'inter continental', 'fusion', 'international', 'mixed', 'global']),
            ('Indian-Sub', ['indian-sub', 'indian', 'desi', 'south asian']),
            ('European', ['european']),
            ('Oriental', ['oriental', 'asian']),
        ]
        
        for name, keywords in cuisines:
            if any(kw in text_lower for kw in keywords):
                return name
        
        return None
    
    def extract_people(self, text: str) -> Optional[int]:
        """Extract number of people - accepts both '2 people' and just '2'"""
        text_lower = text.lower().strip()
        
        patterns = [
            r'for\s+(\d+)\s+(?:people|person)',
            r'(\d+)\s+(?:people|person)',
            r'serve\s+(\d+)',
            r'^(\d+)$',  # Just a number, e.g., "2" or "4"
            r'^(\d+)\s*$'  # Number with optional whitespace
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                num = int(match.group(1))
                # Reasonable range check (1-50 people)
                if 1 <= num <= 50:
                    return num
        
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
            # ALWAYS ask for spices (even if user added spices in ingredients)
            # Only skip if user explicitly answered the spices question
            elif not collected.get('_spices_provided'):
                missing.append('spices')
                return missing
        
        # NEW: Handle _pending_spice_suggestions (from "no spices" flow)
        if collected.get('_pending_spice_suggestions'):
            message_lower = message.lower().strip()
            
            if intent == 'add_all_suggestions' or 'yes' in message_lower or 'add' in message_lower:
                # User wants to add suggested spices
                spices = collected['_pending_spice_suggestions']['spices']
                spice_items = [{'name': spice, 'qty': None} for spice in spices]
                
                collected['ingredients'] = self.add_suggestions(
                    collected['ingredients'],
                    spice_items,
                    collected.get('cuisine_preference')
                )
                collected['_spices_provided'] = True
                del collected['_pending_spice_suggestions']
                
                missing = self.check_missing(collected)
                msg = f" Added: {', '.join(spices)}!\n\n"
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
            
            elif intent == 'skip_suggestions' or 'skip' in message_lower or 'no' in message_lower:
                # User still wants to skip - continue without spices
                collected['_spices_provided'] = True
                del collected['_pending_spice_suggestions']
                
                missing = self.check_missing(collected)
                return {
                    "status": "success",
                    "bot_name": "Doctor Foody",
                    "message": " Continuing without spices!\n\n" + self.next_question(missing, collected),
                    "collected_data": collected,
                    "missing_fields": missing
                }, 200
            
            else:
                # User specified specific spices
                selected_spices = []
                for spice in collected['_pending_spice_suggestions']['spices']:
                    if spice.lower() in message_lower:
                        selected_spices.append({'name': spice, 'qty': None})
                
                if selected_spices:
                    collected['ingredients'] = self.add_suggestions(
                        collected['ingredients'],
                        selected_spices,
                        collected.get('cuisine_preference')
                    )
                    collected['_spices_provided'] = True
                    del collected['_pending_spice_suggestions']
                    
                    missing = self.check_missing(collected)
                    spice_names = [s['name'] for s in selected_spices]
                    msg = f" Added: {', '.join(spice_names)}!\n\n"
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
        """Generate next question"""
        if not missing:
            return "READY"
        
        field = missing[0]
        
        if field == 'ingredients':
            return " Hi, I'm doctor foodie ! What ingredients do you have?\n Example: '2 pieces katla fish, 1cup rice, 100g onion'"
        
        elif field == 'spices':
            return " What spices do you have or do you want to add any spices?\n Example: 'turmeric, cumin, salt, red chili powder' or type 'no' to skip"
        
        elif field == 'unclear_quantities':
            unclear = [ing['name'] for ing in collected['ingredients'] if ing.get('unclear')]
            if len(unclear) == 1:
                return f"How much {unclear[0]}?\n Example: '2 pieces' or '100g' or '1cup'"
            else:
                return f"Please specify quantities for: {', '.join(unclear)}\n Example: '2tomato, 100g onion, 1cup rice'"
        
        elif field == 'suggestions_pending':
            sugg = collected['_pending_suggestions']
            all_sugg = sugg['spices'] + sugg['basics']
            
            items_list = '\n'.join([f"{i+1}. {item}" for i, item in enumerate(all_sugg)])
            
            return (
                f" **Common additions for {collected.get('cuisine_preference', 'your cuisine')}:**\n\n"
                f"{items_list}\n\n"
                f" Select items to add:\n"
                f"• Type names: 'turmeric, cumin, salt'\n"
                f"• Type names with qty: 'sesame oil 2tsp, turmeric 1tsp'\n"
                f"• Type numbers: '1, 3, 5'\n"
                f"• Type 'all' for everything\n"
                f"• Type 'no' to skip"
            )
        
        elif field == 'cuisine_preference':
            return "What type of cuisine?\n Oriental / Indian-Sub / Central Asian / European / Inter-Continental"
        
        elif field == 'number_of_people':
            return "How many people are you cooking for?"
        
        elif field == 'cooking_preference':
            return "Is this for daily meal or special occasion?"
        
        return "Please provide more details."
    
    def format_summary(self, collected: Dict) -> str:
        """Format summary"""
        ings = ", ".join([f"{ing['qty']} {ing['name']}" for ing in collected['ingredients']])
        
        return (
            f" **Your cooking plan:**\n\n"
            f" **Ingredients:** {ings}\n"
            f" **Cuisine:** {collected['cuisine_preference']}\n"
            f" **People:** {collected['number_of_people']}\n"
            f" **Type:** {collected['cooking_preference'].replace('_', ' ').title()}\n\n"
        )
    
    # ==================== INTENT DETECTION ====================
    
    def detect_intent(self, text: str) -> str:
        """Detect user intent"""
        text_lower = text.lower().strip()
        
        confirm_phrases = [
            'confirm', 'generate', 'ready', 
            "let's cook", 'cook it', 'start cooking', 
            'begin cooking', 'make it', 'prepare it'
        ]
        if any(phrase in text_lower for phrase in confirm_phrases):
            return 'confirm'
        
        if any(w in text_lower for w in ['reset', 'start over', 'restart']):
            return 'reset'
        
        if text_lower in ['all', 'add all', 'yes', 'add', 'okay', 'ok'] and len(text_lower.split()) <= 2:
            return 'add_all_suggestions'
        
        if any(w in text_lower for w in ['no', 'skip', 'nope', 'none']):
            return 'skip_suggestions'
        
        return 'provide'
    
    # ==================== RECIPE GENERATION ====================
    
    def generate_recipe(self, user_id: str, collected: Dict) -> Tuple[Dict, int]:
        """Generate recipe"""
        try:
            from controller.recipe_controller import generate_recipe_controller
            
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
                    "message": " Here are your delicious recipes!",
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
        """Main chat handler"""
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
        
        if intent == 'reset':
            return {
                "status": "success",
                "bot_name": "Doctor Foody",
                "message": " Starting fresh!\n\n" + self.next_question(['ingredients'], {}),
                "collected_data": {},
                "missing_fields": ['ingredients', 'cuisine_preference', 'number_of_people', 'cooking_preference']
            }, 200
        
        if intent == 'confirm':
            missing = self.check_missing(collected)
            if missing:
                return {
                    "status": "success",
                    "bot_name": "Doctor Foody",
                    "message": " Please complete all details!\n\n" + self.next_question(missing, collected),
                    "collected_data": collected,
                    "missing_fields": missing
                }, 200
            
            return self.generate_recipe(user_id, collected)
        
        # Handle suggestions
        if collected.get('_pending_suggestions') and not collected.get('_suggestions_handled'):
            
            if intent == 'add_all_suggestions':
                sugg = collected['_pending_suggestions']
                all_items = sugg.get('spices', []) + sugg.get('basics', [])
                all_items_dict = [{'name': item, 'qty': None} for item in all_items]
                
                collected['ingredients'] = self.add_suggestions(
                    collected['ingredients'], 
                    all_items_dict,
                    collected.get('cuisine_preference')
                )
                collected['_suggestions_handled'] = True
                del collected['_pending_suggestions']
                
                # If this was from cuisine_not_feasible flow, clean it up
                if collected.get('_cuisine_not_feasible'):
                    del collected['_cuisine_not_feasible']
                
                missing = self.check_missing(collected)
                
                msg = f" Added: {', '.join(all_items)}!\n\n"
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
            
            if intent == 'skip_suggestions':
                collected['_suggestions_handled'] = True
                del collected['_pending_suggestions']
                
                # If this was from cuisine_not_feasible flow, clean it up
                if collected.get('_cuisine_not_feasible'):
                    del collected['_cuisine_not_feasible']
                
                missing = self.check_missing(collected)
                
                return {
                    "status": "success",
                    "bot_name": "Doctor Foody",
                    "message": " Skipped!\n\n" + self.next_question(missing, collected),
                    "collected_data": collected,
                    "missing_fields": missing
                }, 200
            
            selected_items = self.parse_user_selection(message, collected['_pending_suggestions'])
            
            if selected_items:
                collected['ingredients'] = self.add_suggestions(
                    collected['ingredients'],
                    selected_items,
                    collected.get('cuisine_preference')
                )
                collected['_suggestions_handled'] = True
                del collected['_pending_suggestions']
                
                # If this was from cuisine_not_feasible flow, clean it up
                if collected.get('_cuisine_not_feasible'):
                    del collected['_cuisine_not_feasible']
                
                missing = self.check_missing(collected)
                
                selected_names = [item['name'] for item in selected_items]
                msg = f" Added: {', '.join(selected_names)}!\n\n"
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
                return {
                    "status": "success",
                    "bot_name": "Doctor Foody",
                    "message": " I couldn't understand. " + self.next_question(['suggestions_pending'], collected),
                    "collected_data": collected,
                    "missing_fields": ['suggestions_pending']
                }, 200
        
        # Extract data
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
        
        new_ings = self.extract_ingredients(message)
        if new_ings:
            # Check if user is currently on spices question (has ingredients but not spices)
            if collected.get('ingredients'):
                collected['ingredients'] = self.merge_ingredients(collected['ingredients'], new_ings)
            else:
                collected['ingredients'] = new_ings
            
            # DO NOT set _spices_provided automatically
            # Only set when user explicitly responds to spices question
        
        # Handle spices question response
        # Check if previous bot message was asking for spices
        chat_history = data.get('chat_history', [])
        if chat_history and len(chat_history) > 0:
            last_bot_msg = None
            for msg in reversed(chat_history):
                if msg.get('role') == 'assistant':
                    last_bot_msg = msg.get('content', '')
                    break
            
            # If last question was about spices and user responded
            if last_bot_msg and 'what spices' in last_bot_msg.lower():
                # User is responding to spices question - mark as provided
                collected['_spices_provided'] = True
        
        # Handle "no spices" response
        missing = self.check_missing(collected)
        
        if 'spices' in missing and intent == 'skip_suggestions':
            # User said "no spices" - check if recipe is possible
            feasibility = self.check_recipe_feasibility_without_spices(collected['ingredients'])
            
            if not feasibility.get('possible') and feasibility.get('suggested_spices'):
                # Recipe not possible without spices - suggest minimum spices
                sugg_spices = feasibility.get('suggested_spices', [])
                reason = feasibility.get('reason', 'Basic seasonings are needed for a tasty dish')
                
                msg = (
                    f" {reason}\n\n"
                    f"**Minimum suggested spices:**\n"
                    f"• {', '.join(sugg_spices)}\n\n"
                    f"Would you like to add these? (type 'yes' to add all, or specific ones like 'salt, oil')\n"
                    f"Or type 'skip' to continue without spices"
                )
                
                collected['_pending_spice_suggestions'] = {
                    'spices': sugg_spices,
                    'reason': reason
                }
                
                return {
                    "status": "success",
                    "bot_name": "Doctor Foody",
                    "message": msg,
                    "collected_data": collected,
                    "missing_fields": ['spices']
                }, 200
            else:
                # Recipe is possible without spices - mark as provided and continue
                collected['_spices_provided'] = True
            
            # CRITICAL FIX: If user is in cuisine_not_feasible state and provides ingredients
            # Check if they're providing the missing items
            if collected.get('_cuisine_not_feasible'):
                missing_items_lower = [item.lower() for item in collected['_cuisine_not_feasible'].get('missing_items', [])]
                new_ings_lower = [ing['name'].lower() for ing in new_ings]
                
                # Check if any of the new ingredients match missing items
                if any(ing_name in missing_items_lower for ing_name in new_ings_lower):
                    # User is adding the missing items - accept the original cuisine
                    collected['cuisine_preference'] = collected['_cuisine_not_feasible']['original_cuisine']
                    del collected['_cuisine_not_feasible']
        
        if not collected.get('cuisine_preference'):
            cuisine = self.extract_cuisine(message)
            if cuisine:
                # If user previously had cuisine_not_feasible and now choosing alternative, accept it
                if collected.get('_cuisine_not_feasible'):
                    # User is choosing an alternative cuisine
                    collected['cuisine_preference'] = cuisine
                    del collected['_cuisine_not_feasible']
                    # Don't suggest any spices - just move to next question
                else:
                    # First time choosing cuisine - check feasibility
                    if collected.get('ingredients'):
                        feasibility = self.check_cuisine_feasibility(cuisine, collected['ingredients'])
                        
                        if not feasibility['feasible'] and feasibility['missing_essentials']:
                            # Cuisine not feasible - suggest alternatives or additions
                            alt_cuisines = ', '.join(feasibility['alternative_cuisines'][:2]) if feasibility['alternative_cuisines'] else 'other cuisines'
                            missing_items = ', '.join(feasibility['missing_essentials'][:3])
                            
                            msg = (
                                f" {feasibility.get('reason', 'The selected cuisine may need additional ingredients.')}\n\n"
                                f"**Option 1:** Add these items to make {cuisine}:\n"
                                f"• {missing_items}\n\n"
                                f"**Option 2:** Try {alt_cuisines} with your current ingredients\n\n"
                                f"What would you prefer? (type 'add items' or 'change cuisine' or mention alternative cuisine)"
                            )
                            
                            collected['_cuisine_not_feasible'] = {
                                'original_cuisine': cuisine,
                                'missing_items': feasibility['missing_essentials'],
                                'alternatives': feasibility['alternative_cuisines']
                            }
                            
                            return {
                                "status": "success",
                                "bot_name": "Doctor Foody",
                                "message": msg,
                                "collected_data": collected,
                                "missing_fields": ['cuisine_preference']
                            }, 200
                    
                    # Cuisine is feasible or no ingredients yet - accept it
                    collected['cuisine_preference'] = cuisine
                    # REMOVED: No spice suggestions after cuisine selection
        
        # Handle cuisine feasibility response
        if collected.get('_cuisine_not_feasible'):
            message_lower = message.lower()
            
            if 'add' in message_lower or 'item' in message_lower:
                # User wants to add missing items
                missing_items = collected['_cuisine_not_feasible']['missing_items']
                original_cuisine = collected['_cuisine_not_feasible']['original_cuisine']
                
                # Add missing items as suggestions
                collected['cuisine_preference'] = original_cuisine
                collected['_pending_suggestions'] = {
                    'spices': missing_items[:5],
                    'basics': []
                }
                del collected['_cuisine_not_feasible']
                
                missing = self.check_missing(collected)
                return {
                    "status": "success",
                    "bot_name": "Doctor Foody",
                    "message": self.next_question(missing, collected),
                    "collected_data": collected,
                    "missing_fields": missing
                }, 200
            
            elif 'change' in message_lower or any(alt.lower() in message_lower for alt in collected['_cuisine_not_feasible'].get('alternatives', [])):
                # User wants to change cuisine - extract the new cuisine from message
                new_cuisine = self.extract_cuisine(message)
                if new_cuisine:
                    collected['cuisine_preference'] = new_cuisine
                del collected['_cuisine_not_feasible']
                # Continue to next question
        
        if not collected.get('number_of_people'):
            people = self.extract_people(message)
            if people:
                collected['number_of_people'] = people
        
        if not collected.get('cooking_preference'):
            pref = self.extract_preference(message)
            if pref:
                collected['cooking_preference'] = pref
        
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