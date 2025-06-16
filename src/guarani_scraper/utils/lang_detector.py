from polyglot.detect import Detector
import fasttext
import os
import numpy as np
import nltk
from nltk.tokenize import word_tokenize
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
        "mba'eichagua", "mba'eichapa", "aipo", "upérõ", "upéi", 
        "guaraní", "guarani", "avañe'ẽ", "ñanduti", "paraguay",
        "asunción", "itá", "y", "ka'a", "ka'aguy", "ñandu",
        "teko", "jehe'a", "mandu'a", "porã", "vai", "tuicha",
        "michĩ", "pyahu", "tuja", "karú", "hype", "yvára",
        "aiko", "reiko", "oiko", "ahecha", "rehecha", "ohecha",
        "ahendu", "rehendu", "ohendu", "aipota", "reipota", "oipota",
        "peteĩ", "mokõi", "mbohapy", "irundy", "po", "poteĩ",
        "mbae", "mava", "moo", "anete", "upe", "upei"
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
        Guarani detection using NLTK and linguistic patterns.

        Searches for:
        1. Common Guarani words (stopwords)
        2. Characteristic nasal vowels (ã, ẽ, ĩ, õ, ũ, ỹ)
        3. Typical Guarani morphological patterns

        Args:
            text (str): Text to analyze

        Returns:
            bool: True if text appears to be Guarani
        """
        if len(text) < 10:  # Too short for meaningful analysis
            return False

        try:
            # Tokenize the text (split into words)
            tokens = word_tokenize(text.lower())

            if len(tokens) < 3:  # Need at least 3 words
                return False

            # 1. Count known Guarani words
            guarani_word_count = 0
            found_guarani_words = []
            for token in tokens:
                if token in self.guarani_stopwords:
                    guarani_word_count += 1
                    found_guarani_words.append(token)

            # Ratio of Guarani words
            guarani_ratio = guarani_word_count / len(tokens)

            # 2. Search for nasal vowels (very characteristic of Guarani)
            nasal_vowels = ["ã", "ẽ", "ĩ", "õ", "ũ", "ỹ"]
            nasal_count = 0
            for vowel in nasal_vowels:
                nasal_count += text.lower().count(vowel)

            # 3. Search for Guarani morphological patterns
            guarani_patterns = 0
            found_patterns = []

            # Common suffixes
            suffixes = ["kue", "gua", "va'e", "rã", "ngo", "mi", "piko", "vo"]
            for suffix in suffixes:
                if suffix in text.lower():
                    guarani_patterns += 1
                    found_patterns.append(f"suffix:{suffix}")

            # Common prefixes
            prefixes = ["ñe", "ño", "ñu", "nd", "mb", "ng"]
            for prefix in prefixes:
                if re.search(r"\b" + prefix, text.lower()):
                    guarani_patterns += 1

            # Typical consonant combinations
            consonant_patterns = ["mb", "nd", "ng", "nt", "nh", "ch"]
            for pattern in consonant_patterns:
                guarani_patterns += text.lower().count(pattern)

            # 4. Decision based on multiple criteria
            # It's Guarani if it meets any of these criteria:
            criteria_met = 0

            if guarani_ratio > 0.15:  # 15% or more Guarani words
                criteria_met += 1

            if nasal_count >= 2:  # At least 2 nasal vowels
                criteria_met += 1

            if guarani_patterns >= 3:  # At least 3 morphological patterns
                criteria_met += 1
                
            print(f"DEBUG NLTK: Words: {found_guarani_words}, Ratio: {guarani_ratio:.2f}, Nasal: {nasal_count}, Patterns: {found_patterns}, Criteria: {criteria_met}/3")

            # Need at least 1 criterion to consider it Guarani
            return criteria_met >= 1

        except Exception:
            return False
