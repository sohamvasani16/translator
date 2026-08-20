import time
import logging
from deep_translator import GoogleTranslator

logger = logging.getLogger("translation_service")
logger.setLevel(logging.INFO)

class TranslationService:
    def __init__(self):
        self.cache = {}

    def translate_text(self, text: str, target_lang: str, source_lang: str = "auto") -> str:
        """
        Translates text to target language with caching and error handling.
        """
        if not text or not text.strip():
            return text
        
        cleaned_text = text.strip()
        
        # Don't translate pure numbers or math symbols
        if cleaned_text.replace(".", "").replace(",", "").replace("-", "").isdigit():
            return text

        cache_key = (cleaned_text, source_lang, target_lang)
        if cache_key in self.cache:
            # Maintain leading/trailing whitespace if any
            prefix = text[:len(text) - len(text.lstrip())]
            suffix = text[len(text.rstrip()):]
            return prefix + self.cache[cache_key] + suffix

        # Perform translation with retries
        translated = text
        for attempt in range(3):
            try:
                translator = GoogleTranslator(source=source_lang, target=target_lang)
                result = translator.translate(cleaned_text)
                if result:
                    self.cache[cache_key] = result
                    prefix = text[:len(text) - len(text.lstrip())]
                    suffix = text[len(text.rstrip()):]
                    translated = prefix + result + suffix
                    break
            except Exception as e:
                logger.warning(f"Translation attempt {attempt+1} failed for '{cleaned_text[:20]}...': {e}")
                time.sleep(0.5)

    def translate_batch(self, texts: list, target_lang: str, source_lang: str = "auto") -> list:
        """
        Batch translates a list of text strings in minimal API calls to prevent rate limits.
        """
        if not texts:
            return []

        results = [None] * len(texts)
        indices_to_translate = []
        
        for idx, t in enumerate(texts):
            if not t or not t.strip() or t.strip().replace(".", "").replace(",", "").replace("-", "").isdigit():
                results[idx] = t
            else:
                key = (t.strip(), source_lang, target_lang)
                if key in self.cache:
                    prefix = t[:len(t) - len(t.lstrip())]
                    suffix = t[len(t.rstrip()):]
                    results[idx] = prefix + self.cache[key] + suffix
                else:
                    indices_to_translate.append(idx)

        if not indices_to_translate:
            return results

        # Group remaining items into batch requests using unique block marker
        batch_items = [texts[i].strip() for i in indices_to_translate]
        marker = "\n<<<BLOCK_BREAK>>>\n"
        combined_prompt = marker.join(batch_items)

        translated_combined = None
        for attempt in range(3):
            try:
                translator = GoogleTranslator(source=source_lang, target=target_lang)
                res = translator.translate(combined_prompt)
                if res:
                    translated_combined = res
                    break
            except Exception as e:
                logger.warning(f"Batch translation attempt {attempt+1} failed: {e}")
                time.sleep(0.5)

        if translated_combined:
            parts = translated_combined.split("<<<BLOCK_BREAK>>>")
            if len(parts) == len(batch_items):
                for i, orig_idx in enumerate(indices_to_translate):
                    trans_val = parts[i].strip()
                    orig_text = texts[orig_idx]
                    key = (orig_text.strip(), source_lang, target_lang)
                    self.cache[key] = trans_val
                    
                    prefix = orig_text[:len(orig_text) - len(orig_text.lstrip())]
                    suffix = orig_text[len(orig_text.rstrip()):]
                    results[orig_idx] = prefix + trans_val + suffix
                return results

        # Fallback to individual translations if batch split count mismatched
        for orig_idx in indices_to_translate:
            orig_text = texts[orig_idx]
            results[orig_idx] = self.translate_text(orig_text, target_lang=target_lang, source_lang=source_lang)

        return results

translation_service = TranslationService()
