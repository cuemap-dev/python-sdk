"""Recipe: Using CueMap with local LLM (Ollama/llama.cpp)."""

from cuemap import CueMap

def extract_cues_with_llm(content: str) -> list[str]:
    """
    Extract cues using local LLM.
    
    In real usage, call Ollama or llama.cpp:
    - ollama run llama2 "Extract tags: {content}"
    - Or use llama-cpp-python
    """
    # Mock for demonstration
    # In real usage: call your local LLM
    
    content_lower = content.lower()
    cues = []
    
    # Simple extraction (replace with LLM call)
    words = content_lower.split()
    keywords = [w for w in words if len(w) > 4]
    
    return keywords[:5]


def main():
    print("="*70)
    print("RECIPE: CUEMAP + LOCAL LLM")
    print("="*70)
    
    client = CueMap()
    
    print("\nExample with Ollama:")
    print("""
# Install Ollama: https://ollama.ai
# Run: ollama run llama2

import subprocess
import json

def extract_cues_ollama(content: str) -> list[str]:
    prompt = f'''Extract 3-5 search tags from this text.
Return only a JSON array.

Text: {content}

Tags:'''
    
    result = subprocess.run(
        ["ollama", "run", "llama2", prompt],
        capture_output=True,
        text=True
    )
    
    # Parse JSON response
    tags = json.loads(result.stdout.strip())
    return tags

# Use with CueMap
cues = extract_cues_ollama("I love hiking")
client.add("I love hiking", cues=cues)
    """)
    
    print("\n" + "="*70)
    print("DEMO WITH MOCK LLM")
    print("="*70)
    
    # Demo with mock
    memories = [
        "I love Italian food, especially pizza and pasta",
        "My favorite color is blue, like the ocean",
        "I work as a software engineer at a tech startup"
    ]
    
    for memory in memories:
        cues = extract_cues_with_llm(memory)
        client.add(memory, cues=cues)
        print(f"\n✓ Added: {memory[:50]}...")
        print(f"  Cues: {cues}")
    
    client.close()


if __name__ == "__main__":
    main()
