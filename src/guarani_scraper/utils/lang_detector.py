from polyglot.detect import Detector
import fasttext
import os
import numpy as np
import nltk
import nltk
import re


class GuaraniDetector:
    def __init__(self):
        # Get absolute path to the model file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, "lang_model/lid.176.bin")

        # Load the pretrained model
        self.fasttext_model = fasttext.load_model(model_path)

        # Download required NLTK data (only downloads once)
        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            print("Downloading NLTK punkt tokenizer...")
            nltk.download("punkt")

        # Common Guarani words (basic stopwords)
        self.guarani_stopwords = {
        "ha", "hague", "upéi", "upe", "ko", "katu", "añete", 
        "che", "nde", "aha", "ejú", "oho", "ikatu", "ndaha", 
        "japo", "rejapo", "ojapo", "mba'e", "máva", "moõ",
        "pe", "rehe", "gui", "peve", "rupi", "ndive", "rire",
        "ára", "óga", "mitã", "kuña", "kuimba'e", "sy", "ru",
        "mba'eichagua", "mba'eichapa", "aipo", "upérõ", "upéi"
        , "avañe'ẽ", "ñanduti", 
        "ka'a", "ka'aguy", "ñandu",
        "teko", "jehe'a", "mandu'a", "porã", "vai", "tuicha",
        "michĩ", "pyahu", "tuja", "karú", "hype", "yvára",
        "aiko", "reiko", "oiko", "ahecha", "rehecha", "ohecha",
        "ahendu", "rehendu", "ohendu", "aipota", "reipota", "oipota",
        "peteĩ", "mokõi", "mbohapy", "irundy", "po", "poteĩ",
        "mbae", "mava", "moo", "anete", "upe", "upei",
        "porã", "vai", "tuicha", "michĩ", "pyahu", "tuja", "karú", "hype"
        }

    def is_guarani(self, text):
        """
        Determine if the input text is in the Guarani language.

        Uses a combination of FastText and Polyglot language detection models
        for more accurate identification.

        Both detection methods must agree on the language being Guarani
        for the function to return True, providing higher confidence
        in the language identification.

        Args:
            text (str): The text to analyze for Guarani language

        Returns:
            bool: True if both detection methods identify the text as Guarani,
                  False otherwise or if the text is too short to analyze
        """
        votes = 0

        # Explicit conversion to numpy array if needed
        if isinstance(text, np.ndarray):
            text = str(text)

        # Remove newlines and clean the text
        cleaned_text = text.strip().replace("\n", " ").replace("\r", "")
        
        print(f"DEBUG: Analyzing text (length: {len(cleaned_text)}): '{cleaned_text[:100]}...'")

        # FastText vote
        try:
            prediction = self.fasttext_model.predict(cleaned_text, k=1)
            confidence = prediction[1][0]
            language = prediction[0][0]
            print(f"DEBUG: FastText detected '{language}' with confidence {confidence:.3f}")
            
            if language == "__label__gn" and confidence >= 0.6:
                votes += 1
                print("DEBUG: FastText VOTED for Guarani")
        except Exception as e:
            print(f"FastText detection error: {e}")

        # Polyglot vote
        if len(cleaned_text) >= 100:  
            try:
                detector = Detector(cleaned_text)
                print(f"DEBUG: Polyglot detected '{detector.language.code}' with confidence {detector.language.confidence}")
                
                if detector.language.code == "gn" and detector.language.confidence >= 60:
                    votes += 1
                    print("DEBUG: Polyglot VOTED for Guarani")
            except Exception as e:
                if "longer snippet" not in str(e):
                    print(f"Polyglot detection error: {e}")

        # NLTK vote
        try:
            nltk_result = self._nltk_guarani_check(cleaned_text)
            print(f"DEBUG: NLTK result: {nltk_result}")
            
            if nltk_result:
                votes += 1
                print("DEBUG: NLTK VOTED for Guarani")
        except Exception as e:
            print(f"NLTK detection error: {e}")

        print(f"DEBUG: Total votes: {votes}/3, Result: {'GUARANI' if votes >= 2 else 'NOT GUARANI'}")
        print("=" * 80)

        # Require at least 2 out of 3 detectors to agree
        return votes >= 2


    def _nltk_guarani_check(self, text):
        """
        Guarani detection using linguistic patterns.
        Works for both individual words and text chunks.

        Searches for:
        1. Common Guarani words (stopwords)
        2. Characteristic nasal vowels (ã, ẽ, ĩ, õ, ũ, ỹ)
        3. Typical Guarani morphological patterns

        Args:
            text (str): Text to analyze

        Returns:
            bool: True if text appears to be Guarani
        """
        if len(text) < 2:
            return False

        try:
            # Custom tokenization that preserves Guarani words
            cleaned_for_tokens = text.lower()
            cleaned_for_tokens = re.sub(r'[^\w\sñáéíóúãẽĩõũỹ\']', ' ', cleaned_for_tokens)
            tokens = [token.strip() for token in cleaned_for_tokens.split() if token.strip()]
            
            if len(tokens) == 0:
                return False

            # Lista mínima de palabras españolas MUY comunes
            common_spanish = {
                'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 
                'te', 'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'para', 'del', 
                'los', 'las', 'una', 'como', 'pero', 'fue', 'han', 'más', 'muy',
                'también', 'año', 'años', 'día', 'mundo', 'hombre', 'Paraguay',
                'donde', 'cuando', 'siendo', 'embargo', 'grandes', 'pequeño',
                'segundo', 'nombre', 'cambio', 'ningún', 'mañana', 'paraguayo',
                'paraguaya', 'paraguayos', 'Asunción', 'español', 'española',
                'Brasil', 'Argentina', 'diciembre', 'noviembre', 'señor',
                'señora', 'señores', 'durante', 'después', 'antes', 'siempre',
                'nunca', 'todos', 'todas', 'cada', 'otro', 'otra', 'otros',
                'otras', 'mismo', 'misma', 'primer', 'primera', 'último',
                'última', 'mejor', 'peor', 'mayor', 'menor', 'nuevo', 'nueva',
                'viejo', 'vieja', 'bueno', 'buena', 'malo', 'mala', 'Paraguay',
                'Guaraní', 'Asunción'
            }

            # For single words, use STRICTER logic
            if len(tokens) == 1:
                word = tokens[0]
                
                # REJECT obvious Spanish words
                if word in common_spanish:
                    return False
                
                # REJECT if it's too short for meaningful detection
                if len(word) < 3:
                    return False
                
                # REJECT if it has Spanish patterns but no Guarani patterns
                has_spanish_patterns = (
                    word.endswith(('ción', 'sión', 'dad', 'idad', 'mente', 'ando', 'endo', 'iero', 'iera')) or
                    word.startswith(('des', 'pre', 'sub', 'sobre', 'anti', 'contra')) or
                    re.search(r'(ll|rr|ch(?![eẽ])|qu[eiu])', word)  # Spanish clusters (but not che, chẽ)
                )
                
                has_guarani_patterns = (
                    re.search(r'[ãẽĩõũỹ]', word) or  # Nasal vowels
                    "'" in word or                    # Apostrophe
                    word in self.guarani_stopwords or # Known Guarani
                    re.search(r'(kue|gua|va.e|rã|ngo|piko|hague|rangue)$', word) or  # Guarani morphemes
                    re.search(r'^(ñe|ño|ñu|nd|mb|ng)', word)  # Guarani prefixes
                )
                
                # If it looks Spanish and doesn't look Guarani, reject
                if has_spanish_patterns and not has_guarani_patterns:
                    print(f"DEBUG NLTK: Rejected Spanish-looking word: '{word}'")
                    return False
                
                # Direct match with known Guarani words (highest priority)
                if word in self.guarani_stopwords:
                    print(f"DEBUG NLTK: Found known Guarani word: '{word}'")
                    return True
                
                # Must have MULTIPLE Guarani characteristics for unknown words
                guarani_score = 0
                
                # Has nasal vowels (strong indicator)
                if re.search(r'[ãẽĩõũỹ]', word):
                    guarani_score += 3
                    print(f"DEBUG NLTK: Word '{word}' has nasal vowels (+3)")
                
                # Has apostrophe (very characteristic)
                if "'" in word:
                    guarani_score += 3
                    print(f"DEBUG NLTK: Word '{word}' has apostrophe (+3)")
                
                # Has typical Guarani consonant clusters at word boundaries
                if re.search(r'\b(mb|nd|ng)', word):
                    guarani_score += 2
                    print(f"DEBUG NLTK: Word '{word}' has Guarani consonant clusters (+2)")
                    
                # Has ñ (common in Guarani)
                if 'ñ' in word:
                    guarani_score += 1
                    print(f"DEBUG NLTK: Word '{word}' has ñ (+1)")
                
                # Has typical Guarani morphemes
                if re.search(r'(kue|gua|va.e|rã|ngo|piko|mi|hague|rangue)$', word):
                    guarani_score += 2
                    print(f"DEBUG NLTK: Word '{word}' has Guarani morphemes (+2)")
                
                print(f"DEBUG NLTK: Word '{word}' total score: {guarani_score}")
                
                # Require score >= 4 for single words (stricter than before)
                return guarani_score >= 4
            
            # For text chunks, use existing logic but with Spanish filtering
            else:
                # Filter out Spanish words from tokens
                filtered_tokens = [token for token in tokens if token not in common_spanish]
                
                if len(filtered_tokens) == 0:
                    print("DEBUG NLTK: All tokens filtered out as Spanish")
                    return False
                
                print(f"DEBUG NLTK: Analyzing chunk with {len(filtered_tokens)} filtered tokens")
                
                # Count Guarani words from filtered tokens
                guarani_word_count = 0
                found_guarani_words = []
                
                for token in filtered_tokens:
                    if token in self.guarani_stopwords:
                        guarani_word_count += 1
                        found_guarani_words.append(token)
                    else:
                        # Partial matching for longer words
                        for guarani_word in self.guarani_stopwords:
                            if len(guarani_word) > 3 and guarani_word in token:
                                guarani_word_count += 0.5
                                found_guarani_words.append(f"{token}~{guarani_word}")
                                break
                        
                guarani_ratio = guarani_word_count / len(filtered_tokens)
                
                # Count nasal vowels
                nasal_count = sum(text.lower().count(vowel) for vowel in ["ã", "ẽ", "ĩ", "õ", "ũ", "ỹ"])
                
                # Count patterns (but be more strict about Spanish context)
                pattern_count = 0
                patterns = ["mb", "nd", "ng", "ñ", "kue", "gua", "va'e", "rã", "ngo", "mi", "piko"]
                for pattern in patterns:
                    # Only count if not in obvious Spanish context
                    if pattern in text.lower():
                        # Check for Spanish words that contain these patterns
                        spanish_false_positives = {
                            'mb': ['también', 'embargo', 'nombre', 'hombre', 'iembre', 'iembre'],
                            'nd': ['cuando', 'segundo', 'mundo', 'donde', 'durante'],
                            'ng': ['lenguaje', 'ningún', 'español'],
                            'ñ': ['año', 'años', 'señor', 'señora', 'mañana', 'español', 'pequeño']
                        }
                        
                        if pattern in spanish_false_positives:
                            # Don't count if any Spanish false positive is present
                            if not any(spanish_word in text.lower() for spanish_word in spanish_false_positives[pattern]):
                                pattern_count += text.lower().count(pattern)
                        else:
                            pattern_count += text.lower().count(pattern)
                
                # HIGHER thresholds for better precision
                criteria_met = 0
                reasons = []
                
                if guarani_ratio > 0.20:  # Increased from 0.15 to 0.20 (20%)
                    criteria_met += 1
                    reasons.append(f"words:{guarani_ratio:.2f}")
                    
                if nasal_count >= 2:      # Keep at 2
                    criteria_met += 1
                    reasons.append(f"nasal:{nasal_count}")
                    
                if pattern_count >= 3:    # Increased from 2 to 3
                    criteria_met += 1
                    reasons.append(f"patterns:{pattern_count}")
                
                print(f"DEBUG NLTK: Found words: {found_guarani_words}")
                    
                return criteria_met >= 2  # Require 2 out of 3 criteria

        except Exception as e:
            print(f"DEBUG NLTK: Exception: {e}")
            return False