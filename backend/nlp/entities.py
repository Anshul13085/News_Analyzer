# backend/nlp/entities.py
# This is how your entity extraction module should look to fix the validation error

import logging
from typing import List, Dict, Optional
import spacy
from transformers import pipeline

logger = logging.getLogger(__name__)

# Load your NER model (adjust based on your actual implementation)
try:
    nlp = spacy.load("en_core_web_sm")
    logger.info("Spacy model loaded successfully")
except OSError:
    logger.warning("Spacy model not found, falling back to transformers")
    nlp = None

# Alternative: Use transformers NER pipeline
try:
    ner_pipeline = pipeline("ner", 
                           model="dbmdz/bert-large-cased-finetuned-conll03-english",
                           aggregation_strategy="simple")
    logger.info("Transformers NER pipeline loaded successfully")
except Exception as e:
    logger.error(f"Failed to load transformers NER pipeline: {e}")
    ner_pipeline = None

def extract_entities(text: str) -> List[Dict]:
    """
    Extract named entities from text with proper validation.
    Returns a list of dictionaries with entity information.
    """
    if not text or not isinstance(text, str):
        logger.warning("Invalid text provided for entity extraction")
        return []
    
    entities = []
    
    try:
        # Method 1: Try Spacy first
        if nlp:
            entities.extend(_extract_with_spacy(text))
        
        # Method 2: Fallback to transformers
        elif ner_pipeline:
            entities.extend(_extract_with_transformers(text))
        
        else:
            logger.warning("No NER models available")
            return []
        
        # Filter and validate entities
        validated_entities = _validate_entities(entities)
        
        logger.debug(f"Extracted {len(validated_entities)} valid entities from {len(entities)} candidates")
        return validated_entities
        
    except Exception as e:
        logger.error(f"Entity extraction failed: {str(e)}")
        return []

def _extract_with_spacy(text: str) -> List[Dict]:
    """Extract entities using Spacy NER"""
    entities = []
    
    try:
        doc = nlp(text[:1000])  # Limit text length to avoid memory issues
        
        for ent in doc.ents:
            if ent.text and len(ent.text.strip()) > 1:  # Filter out single characters
                entities.append({
                    "name": ent.text.strip(),
                    "type": ent.label_.lower(),
                    "sentiment": "neutral",  # Default sentiment
                    "bias": None,
                    "score": 0.9,  # High confidence for Spacy
                    "start": ent.start_char,
                    "end": ent.end_char
                })
    
    except Exception as e:
        logger.error(f"Spacy entity extraction failed: {str(e)}")
    
    return entities

def _extract_with_transformers(text: str) -> List[Dict]:
    """Extract entities using transformers pipeline"""
    entities = []
    
    try:
        # Limit text length to avoid memory issues
        truncated_text = text[:512]
        results = ner_pipeline(truncated_text)
        
        for result in results:
            if result.get('word') and len(result['word'].strip()) > 1:
                entities.append({
                    "name": result['word'].strip(),
                    "type": result.get('entity_group', 'misc').lower(),
                    "sentiment": "neutral",
                    "bias": None,
                    "score": result.get('score', 0.5),
                    "start": result.get('start'),
                    "end": result.get('end')
                })
    
    except Exception as e:
        logger.error(f"Transformers entity extraction failed: {str(e)}")
    
    return entities

def _validate_entities(entities: List[Dict]) -> List[Dict]:
    """
    Validate and clean entity data to prevent Pydantic validation errors
    """
    validated = []
    
    for entity in entities:
        try:
            # Ensure name is not None and is a valid string
            name = entity.get("name")
            if not name or not isinstance(name, str):
                logger.debug(f"Skipping entity with invalid name: {name}")
                continue
            
            # Clean the name
            name = name.strip()
            if not name or len(name) < 2:
                logger.debug(f"Skipping entity with too short name: '{name}'")
                continue
            
            # Remove entities that are just punctuation or numbers
            if name.isdigit() or all(c in '.,!?;:()-[]{}"\'' for c in name):
                logger.debug(f"Skipping punctuation/number entity: '{name}'")
                continue
            
            # Ensure other fields have valid values
            validated_entity = {
                "name": name,
                "type": str(entity.get("type", "misc")).lower(),
                "sentiment": str(entity.get("sentiment", "neutral")).lower(),
                "bias": entity.get("bias"),  # Can be None
                "score": float(entity.get("score", 0.5)) if entity.get("score") is not None else 0.5
            }
            
            # Additional validation for sentiment
            if validated_entity["sentiment"] not in ["positive", "negative", "neutral"]:
                validated_entity["sentiment"] = "neutral"
            
            validated.append(validated_entity)
            
        except Exception as e:
            logger.warning(f"Error validating entity {entity}: {str(e)}")
            continue
    
    # Remove duplicates based on name (case-insensitive)
    seen_names = set()
    unique_entities = []
    
    for entity in validated:
        name_lower = entity["name"].lower()
        if name_lower not in seen_names:
            seen_names.add(name_lower)
            unique_entities.append(entity)
    
    return unique_entities

# Additional utility functions
def get_entity_sentiment(entity_name: str, context: str) -> str:
    """
    Analyze sentiment for a specific entity in context.
    This is a placeholder - implement based on your needs.
    """
    # Simple sentiment analysis based on surrounding words
    # You can implement more sophisticated sentiment analysis here
    positive_words = ["good", "great", "excellent", "positive", "success", "win"]
    negative_words = ["bad", "terrible", "awful", "negative", "failure", "lose"]
    
    context_lower = context.lower()
    
    # Simple keyword-based sentiment
    positive_count = sum(1 for word in positive_words if word in context_lower)
    negative_count = sum(1 for word in negative_words if word in context_lower)
    
    if positive_count > negative_count:
        return "positive"
    elif negative_count > positive_count:
        return "negative"
    else:
        return "neutral"

# Test function
def test_entity_extraction():
    """Test the entity extraction with sample text"""
    sample_text = """
    President Joe Biden met with Prime Minister Narendra Modi in Washington D.C. 
    They discussed climate change and economic cooperation between the United States and India.
    Apple Inc. announced new products while Google continues to innovate in AI.
    """
    
    entities = extract_entities(sample_text)
    
    print("Extracted entities:")
    for entity in entities:
        print(f"- {entity['name']} ({entity['type']}) - {entity['sentiment']}")
    
    return entities

if __name__ == "__main__":
    test_entity_extraction()