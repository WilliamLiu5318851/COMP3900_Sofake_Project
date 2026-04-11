import re

def validate_news_content(content: str):
    if content is None:
        return False, "News content is required."
    
    content = content.strip()

    if not content:
        return False, "News content cannot be empty"
    
    if len(content) < 20:
            return False, "News content is too short (minimum 20 characters)."
    
    if len(content) > 5000:
         return False, "News content is too long (maximum 5000 characters)."   
    
    if not re.search(r"[A-Za-z0-9]", content):
         return False, "News content must contain meaningful text."
    
    words = re.findall(r"\b[A-Za-z]{2,}\b", content)
    if len(words) < 5:
        return False, "Content does not contain enough meaningful words."
    
    return True, "Valid content"
    
