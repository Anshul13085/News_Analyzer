from transformers import pipeline
from backend.config import SUMMARIZER_MODEL, MAX_SUMMARY_TOKENS
import logging

logger = logging.getLogger(__name__)

_summarizer = None

def get_summarizer():
    global _summarizer
    if _summarizer is None:
        try:
            _summarizer = pipeline(
                "summarization",
                model=SUMMARIZER_MODEL,  # optional: use default if None
                framework="pt"   # force PyTorch, avoids TF issues
                # Remove tokenizer_kwargs - this was causing the error
            )
            logger.info(f"Summarizer loaded successfully with model: {SUMMARIZER_MODEL}")
            
            # Test the summarizer after creation
            test_result = _summarizer(
                "This is a test sentence to verify the summarizer is working correctly.", 
                max_length=50,
                min_length=10,
                do_sample=False,
                truncation=True
            )
            logger.info("Summarizer test successful")
            
        except Exception as e:
            logger.error(f"Failed to load summarizer: {str(e)}")
            raise
    return _summarizer

def truncate_for_model(text: str, max_tokens: int = 900) -> str:
    """
    Truncate text to fit within model's maximum input length.
    Leaves some buffer for special tokens.
    """
    if not text:
        return text
    
    # Rough approximation: 1 token ≈ 4 characters for English
    max_chars = max_tokens * 4
    
    if len(text) <= max_chars:
        return text
    
    # Try to truncate at sentence boundaries
    truncated = text[:max_chars]
    
    # Find the last complete sentence
    last_period = truncated.rfind('.')
    last_exclamation = truncated.rfind('!')
    last_question = truncated.rfind('?')
    
    last_sentence_end = max(last_period, last_exclamation, last_question)
    
    # If we found a sentence boundary in the last 20% of the truncated text
    if last_sentence_end > max_chars * 0.8:
        return truncated[:last_sentence_end + 1].strip()
    
    # Otherwise, truncate at word boundary
    last_space = truncated.rfind(' ')
    if last_space > max_chars * 0.9:
        return truncated[:last_space].strip()
    
    # Last resort: hard truncate
    return truncated.strip()

def summarize(text: str, max_tokens: int = MAX_SUMMARY_TOKENS) -> str:
    """
    Summarize text with proper error handling and input length management.
    """
    try:
        if not text or not text.strip():
            logger.warning("Empty text provided for summarization")
            return ""
        
        # Check if text is too short to summarize
        word_count = len(text.split())
        if word_count < 40:
            logger.info(f"Text too short to summarize ({word_count} words)")
            return text
        
        # Truncate text to fit model constraints
        truncated_text = truncate_for_model(text, max_tokens=900)
        logger.info(f"Input text truncated from {len(text)} to {len(truncated_text)} characters")
        
        # Ensure max_tokens doesn't exceed model capabilities
        max_tokens = min(max_tokens, 512)  # Most summarization models cap at 512
        min_tokens = max(30, int(max_tokens/3))
        
        # Ensure min_length doesn't exceed max_length
        min_tokens = min(min_tokens, max_tokens - 10)
        
        logger.info(f"Summarizing with max_length={max_tokens}, min_length={min_tokens}")
        
        summarizer = get_summarizer()
        result = summarizer(
            truncated_text,
            max_length=max_tokens,
            min_length=min_tokens,
            do_sample=False,
            truncation=True  # Let the model handle truncation internally
        )
        
        if result and len(result) > 0 and "summary_text" in result[0]:
            summary = result[0]["summary_text"].strip()
            logger.info(f"Summary generated successfully: {len(summary)} characters")
            return summary
        else:
            logger.warning("Summarizer returned unexpected format")
            return ""
            
    except Exception as e:
        logger.error(f"Summarization failed: {str(e)}")
        # Return first few sentences as fallback
        sentences = text.split('.')[:3]
        fallback = '. '.join(sentences).strip()
        if fallback and not fallback.endswith('.'):
            fallback += '.'
        logger.info("Using fallback summarization (first 3 sentences)")
        return fallback

def test_summarizer():
    """
    Test function to verify summarizer is working
    """
    test_text = """
    Artificial intelligence (AI) is intelligence demonstrated by machines, 
    in contrast to the natural intelligence displayed by humans and animals. 
    Leading AI textbooks define the field as the study of "intelligent agents": 
    any device that perceives its environment and takes actions that maximize 
    its chance of successfully achieving its goals. Colloquially, the term 
    "artificial intelligence" is often used to describe machines that mimic 
    "cognitive" functions that humans associate with the human mind, such as 
    "learning" and "problem solving". As machines become increasingly capable, 
    tasks considered to require "intelligence" are often removed from the 
    definition of AI, a phenomenon known as the AI effect.
    """
    
    try:
        result = summarize(test_text)
        print(f"Test successful. Summary: {result}")
        return True
    except Exception as e:
        print(f"Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Run test when script is executed directly
    test_summarizer()