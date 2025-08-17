# backend/nlp/bias.py
from transformers import pipeline
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_bias_classifier = None

def get_bias_classifier():
    global _bias_classifier
    if _bias_classifier is None:
        try:
            # Using zero-shot classification for bias detection - remove tokenizer_kwargs
            _bias_classifier = pipeline(
                "zero-shot-classification",
                model="joeddav/xlm-roberta-large-xnli",
                framework="pt"
                # Remove tokenizer_kwargs - this was causing issues
            )
            logger.info("Bias classifier loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load bias classifier: {str(e)}")
            raise
    return _bias_classifier

def truncate_text(text: str, max_length: int = 300) -> str:
    """Truncate text for bias analysis"""
    if len(text) <= max_length * 4:  # rough char to token ratio
        return text
    
    truncated = text[:max_length * 4]
    last_space = truncated.rfind(' ')
    if last_space > len(truncated) * 0.8:
        return truncated[:last_space]
    return truncated

def classify_bias(text: str) -> tuple[str, float]:
    """
    Classify political bias of text.
    Returns: (bias_label, confidence_score)
    """
    try:
        if not text or not text.strip():
            logger.warning("Empty text provided for bias analysis")
            return "neutral", 0.0
        
        # Truncate text to avoid sequence length issues
        truncated_text = truncate_text(text)
        logger.info(f"Analyzing bias for text: {truncated_text[:100]}...")
        
        # Define bias categories
        candidate_labels = ["liberal", "conservative", "neutral", "left-wing", "right-wing"]
        
        classifier = get_bias_classifier()
        result = classifier(truncated_text, candidate_labels)
        
        if result and 'labels' in result and 'scores' in result:
            top_label = result['labels'][0]
            top_score = result['scores'][0]
            
            logger.info(f"Raw bias result: {top_label} ({top_score:.3f})")
            
            # Normalize bias labels
            if top_label in ['liberal', 'left-wing']:
                bias = 'left-leaning'
            elif top_label in ['conservative', 'right-wing']:
                bias = 'right-leaning'
            else:
                bias = 'neutral'
            
            logger.info(f"Bias classified: {bias} (score: {top_score:.3f})")
            return bias, float(top_score)
        
        logger.warning("No result from bias classifier")
        return "neutral", 0.0
        
    except Exception as e:
        logger.error(f"Bias classification failed: {str(e)}")
        return "neutral", 0.0

def test_bias():
    """Test bias analysis with various texts"""
    test_texts = [
        "The progressive policies will help working families and reduce inequality in our society.",
        "Traditional values and free market solutions are the key to economic prosperity and stability.",
        "The weather forecast shows rain is expected tomorrow across the region.",
        "The government announced new policies that economists say could have mixed effects on different sectors."
    ]
    
    print("Testing Bias Analysis:")
    print("=" * 60)
    
    for i, text in enumerate(test_texts, 1):
        print(f"\nTest {i}: {text}")
        try:
            bias, score = classify_bias(text)
            print(f"Result: {bias.upper()} (confidence: {score:.3f})")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    print("\n" + "=" * 60)
    print("Bias analysis test complete!")

def test_all_nlp():
    """Test both sentiment and bias analysis"""
    try:
        from backend.nlp.sentiment import classify_sentiment
    except:
        print("Could not import sentiment classifier")
        return
    
    test_text = """
    The new government initiative aims to boost economic growth through increased infrastructure spending.
    Critics argue that this approach may lead to higher taxes, while supporters believe it will create jobs
    and improve long-term competitiveness. The policy has generated significant debate among economists
    and political analysts across the spectrum.
    """
    
    print("Testing Complete NLP Pipeline:")
    print("=" * 60)
    print(f"Text: {test_text.strip()}")
    print()
    
    # Test sentiment
    try:
        sentiment, sent_score = classify_sentiment(test_text)
        print(f"Sentiment: {sentiment.upper()} (confidence: {sent_score:.3f})")
    except Exception as e:
        print(f"Sentiment analysis failed: {e}")
    
    # Test bias
    try:
        bias, bias_score = classify_bias(test_text)
        print(f"Bias: {bias.upper()} (confidence: {bias_score:.3f})")
    except Exception as e:
        print(f"Bias analysis failed: {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_bias()
    print("\n")
    test_all_nlp()