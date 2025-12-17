"""Recipe: Using CueMap with OpenAI for auto-tagging."""

from cuemap import CueMap
import json

# Mock OpenAI for demonstration
class MockOpenAI:
    """Mock OpenAI client for demonstration."""
    
    @staticmethod
    def extract_tags(content: str) -> list[str]:
        """Extract tags using 'AI' (mocked for demo)."""
        # In real usage, this would call OpenAI API
        # For demo, we'll use simple rules
        
        content_lower = content.lower()
        tags = []
        
        # Category detection
        if any(word in content_lower for word in ["love", "like", "enjoy", "favorite"]):
            tags.append("preferences")
        
        if any(word in content_lower for word in ["work", "job", "career", "engineer"]):
            tags.append("work")
        
        if any(word in content_lower for word in ["hobby", "hobbies", "recreation", "fun"]):
            tags.append("hobbies")
        
        # Extract nouns (simple approach)
        words = content_lower.split()
        nouns = [w for w in words if len(w) > 4 and w not in [
            "especially", "really", "about", "would", "could", "should"
        ]]
        
        tags.extend(nouns[:5])
        
        return list(set(tags))[:7]  # Max 7 tags


def main():
    print("="*70)
    print("RECIPE: CUEMAP + OPENAI AUTO-TAGGING")
    print("="*70)
    
    client = CueMap()
    openai = MockOpenAI()  # Replace with real OpenAI client
    
    # Helper function
    def smart_add(content: str) -> str:
        """Add memory with AI-generated tags."""
        # Step 1: Ask AI for tags
        cues = openai.extract_tags(content)
        
        print(f"\nContent: {content}")
        print(f"AI-extracted cues: {cues}")
        
        # Step 2: Store in CueMap
        memory_id = client.add(content, cues=cues)
        print(f"✓ Stored: {memory_id}")
        
        return memory_id
    
    # Add memories with AI tagging
    print("\nAdding memories with AI-generated tags...")
    
    smart_add("I love Italian food, especially pizza and pasta")
    smart_add("My favorite color is blue, like the ocean")
    smart_add("I work as a software engineer at a tech startup")
    smart_add("I enjoy hiking in the mountains on weekends")
    
    # Query
    print("\n" + "="*70)
    print("QUERYING")
    print("="*70)
    
    queries = [
        ["preferences", "italian"],
        ["work", "engineer"],
        ["hobbies", "hiking"]
    ]
    
    for cues in queries:
        print(f"\nCues: {cues}")
        results = client.recall(cues, limit=1)
        
        if results:
            print(f"✅ {results[0].content}")
        else:
            print("❌ No results")
    
    print("\n" + "="*70)
    print("REAL OPENAI INTEGRATION")
    print("="*70)
    
    print("""
# Real implementation with OpenAI:

import openai
from cuemap import CueMap

client = CueMap()

def extract_cues_with_openai(content: str) -> list[str]:
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": "Extract 3-5 search tags from the text. "
                          "Return only a JSON array of strings."
            },
            {
                "role": "user",
                "content": content
            }
        ],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)["tags"]

# Use it
cues = extract_cues_with_openai("I love hiking in the mountains")
client.add("I love hiking in the mountains", cues=cues)
    """)
    
    client.close()


if __name__ == "__main__":
    main()
