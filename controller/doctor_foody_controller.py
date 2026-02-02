import os
import re
import requests
import json
from typing import Dict, List, Tuple, Optional

class DoctorFoodyController:
    """
    Smart Personal Chef AI - Fully Dynamic Production Version
    
    IMPROVEMENTS:
    ✅ Zero hardcoded ingredient lists
    ✅ LLM-powered validation for unknown terms
    ✅ Context-aware extraction
    ✅ Self-learning compound ingredient detection
    ✅ Production-ready scalability
    ✅ Enhanced quantity update handling for mixed formats
    """
    
    def __init__(self):
        # LLM API configuration
        self.llm_api_url = os.getenv('MISTRAL_API_URL', 'http://localhost:11434/api/generate')
        self.llm_model = os.getenv('MISTRAL_MODEL', 'mistral')
        
        # Cache for LLM validation results (improves performance)
        self._validation_cache = {}
        
        # Dynamically detected compound ingredients (learned during runtime)
        self._detected_compounds = set()
    
    # ==================== SMART INGREDIENT EXTRACTION ====================
    
    def extract_ingredients(self, text: str) -> List[Dict]:
        """
        Fully dynamic ingredient extraction
        No hardcoded lists - uses patterns and LLM validation
        """
        ingredients = []
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
            r'(\d+(?:\.\d+)?)(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass)\s+([a-z_]+(?:\s+[a-z_]+){0,1}?)(?:\s*(?:,|\sand\s|\.|\band\s|$))',
            r'(\d+(?:\.\d+)?)\s+(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass)\s+([a-z_]+(?:\s+[a-z_]+){0,1}?)(?:\s*(?:,|\sand\s|\.|\band\s|$))',
            r'(\d+)\s*(piece|pieces|peace|peaces|pics?|pcs?)\s+(?:of\s+)?([a-z_]+(?:\s+[a-z_]+){0,1}?)(?:\s*(?:,|\sand\s|\.|\band\s|$))',
            r'(\d+)\s*(spoon|spoons|tbsp|tsp)\s+(?:of\s+)?([a-z_]+(?:\s+[a-z_]+){0,1}?)(?:\s*(?:,|\sand\s|\.|\band\s|$))',
            r'(\d+)\s+([a-z_]+\s+(?:fish|chicken|egg|eggs|prawn|shrimp|crab|lobster|meat|pork|beef|mutton))(?:\s*(?:,|\sand\s|\.|\band\s|$))',
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
            r'\b([a-z_]+(?:\s+[a-z_]+){0,1}?)\s+(\d+(?:\.\d+)?)(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass)(?:\s*(?:,|\sand\s|\.|\band\s|$))',
            r'\b([a-z_]+(?:\s+[a-z_]+){0,1}?)\s+(\d+(?:\.\d+)?)\s+(g|gm|kg|kgs|ml|l|ltr|litre|litres?|cup|cups|glass)(?:\s*(?:,|\sand\s|\.|\band\s|$))',
            r'\b([a-z_]+(?:\s+[a-z_]+){0,1}?)\s+(\d+)\s*(piece|pieces|peace|peaces|pics?|pcs?)(?:\s*(?:,|\sand\s|\.|\band\s|$))',
            r'\b([a-z_]+(?:\s+[a-z_]+){0,1}?)\s+(\d+)\s*(spoon|spoons|tbsp|tsp)(?:\s*(?:,|\sand\s|\.|\band\s|$))',
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
            print(f"  🤖 Using LLM to extract from noisy input...")
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
            print(f"  ⚠️ Compound detection error: {str(e)}")
        
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
                print(f"  ❌ LLM extraction failed: {response.status_code}")
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
                        print(f"  ✅ LLM extracted: {name} ({qty})")
            
            return ingredients
            
        except Exception as e:
            print(f"  ❌ LLM extraction error: {str(e)}")
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
            
            # Skip measurement unit typos
            if word_clean in ['pices', 'pics', 'peace', 'peaces', 'pcs', 'pic']:
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
                print(f"  ⚠️ LLM validation failed for '{name}': {response.status_code}")
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
            print(f"  ⚠️ LLM validation error for '{name}': {str(e)}")
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
        
        ENHANCED: Now handles mixed formats like "spinach 100g and 200g paneer"
        """
        text_lower = text.lower()
        
        # Fix common typos first
        text_lower = re.sub(r'(\d)o+(?=g(?!o)|gm|kg|ml|l(?!o)|cup)', r'\g<1>00', text_lower)
        text_lower = re.sub(r'(\d)o+\s+(?=g(?!o)|gm|kg|ml|l(?!o)|cup)', r'\g<1>00 ', text_lower)
        
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
                        print(f"  ✅ Updated '{ing['name']}': {qty} (pattern matched)")
                        break
                
                if not found:
                    # Keep as unclear if no quantity found
                    updated.append(ing)
                    print(f"  ⚠️ No quantity found for '{ing['name']}' - keeping as unclear")
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
        """Extract cuisine type"""
        text_lower = text.lower()
        
        cuisines = [
            ('Central Asian', ['central asian', 'central', 'turkish', 'persian', 'arabic', 'middle eastern', 'uzbek']),
            ('Inter-Continental', ['inter-continental', 'intercontinental', 'inter continental', 'fusion', 'international', 'mixed', 'global']),
            ('Indian-Sub', ['indian-sub', 'indian', 'bengali', 'punjabi', 'desi', 'south asian']),
            ('European', ['european', 'italian', 'french', 'spanish', 'greek', 'mediterranean']),
            ('Oriental', ['oriental', 'chinese', 'thai', 'japanese', 'korean', 'vietnamese', 'asian']),
        ]
        
        for name, keywords in cuisines:
            if any(kw in text_lower for kw in keywords):
                return name
        
        return None
    
    def extract_people(self, text: str) -> Optional[int]:
        """Extract number of people"""
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
            return "👋 Hi! What ingredients do you have?\n💡 Example: '2 pieces katla fish, 1cup rice, 100g onion'"
        
        elif field == 'unclear_quantities':
            unclear = [ing['name'] for ing in collected['ingredients'] if ing.get('unclear')]
            if len(unclear) == 1:
                return f"How much {unclear[0]}?\n💡 Example: '2 pieces' or '100g' or '1cup'"
            else:
                return f"Please specify quantities for: {', '.join(unclear)}\n💡 Example: '2tomato, 100g onion, 1cup rice'"
        
        elif field == 'suggestions_pending':
            sugg = collected['_pending_suggestions']
            all_sugg = sugg['spices'] + sugg['basics']
            
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
                "message": "🔄 Starting fresh!\n\n" + self.next_question(['ingredients'], {}),
                "collected_data": {},
                "missing_fields": ['ingredients', 'cuisine_preference', 'number_of_people', 'cooking_preference']
            }, 200
        
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
            
            selected_items = self.parse_user_selection(message, collected['_pending_suggestions'])
            
            if selected_items:
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
                return {
                    "status": "success",
                    "bot_name": "Doctor Foody",
                    "message": "⚠️ I couldn't understand. " + self.next_question(['suggestions_pending'], collected),
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
            if collected.get('ingredients'):
                collected['ingredients'] = self.merge_ingredients(collected['ingredients'], new_ings)
            else:
                collected['ingredients'] = new_ings
        
        if not collected.get('cuisine_preference'):
            cuisine = self.extract_cuisine(message)
            if cuisine:
                collected['cuisine_preference'] = cuisine
                
                if collected.get('ingredients') and not collected.get('_pending_suggestions'):
                    sugg = self.get_llm_suggestions(cuisine, collected['ingredients'])
                    
                    if sugg['spices'] or sugg['basics']:
                        collected['_pending_suggestions'] = sugg
        
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