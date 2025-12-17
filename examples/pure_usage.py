"""Pure CueMap usage - no magic, just speed."""

from cuemap import CueMap

def main():
    print("="*70)
    print("CUEMAP: REDIS FOR AI AGENTS")
    print("Pure, Fast, Predictable")
    print("="*70)
    
    client = CueMap()
    
    # Add memories with explicit cues
    print("\nAdding memories with explicit cues...")
    
    client.add(
        "I love Italian food, especially pizza and pasta",
        cues=["food", "italian", "pizza", "pasta", "preferences"]
    )
    print("✓ Food memory")
    
    client.add(
        "My favorite color is blue, like the ocean",
        cues=["color", "blue", "favorite", "preferences"]
    )
    print("✓ Color memory")
    
    client.add(
        "I work as a software engineer at a tech startup",
        cues=["work", "job", "engineer", "software", "career"]
    )
    print("✓ Work memory")
    
    client.add(
        "I enjoy hiking in the mountains on weekends",
        cues=["hobbies", "hiking", "mountains", "outdoor", "recreation"]
    )
    print("✓ Hobbies memory")
    
    # Query with explicit cues
    print("\n" + "="*70)
    print("QUERYING WITH EXPLICIT CUES")
    print("="*70)
    
    queries = [
        (["food"], "Food preferences"),
        (["color", "favorite"], "Favorite color"),
        (["work"], "Work information"),
        (["hobbies"], "Hobbies")
    ]
    
    for cues, description in queries:
        print(f"\nQuery: {description}")
        print(f"Cues: {cues}")
        
        results = client.recall(cues, limit=1)
        
        if results:
            print(f"✅ {results[0].content}")
            print(f"   Score: {results[0].score:.2f}")
            print(f"   Intersection: {results[0].intersection_count}")
        else:
            print("❌ No results")
    
    # Show the power of intersection
    print("\n" + "="*70)
    print("INTERSECTION SCORING DEMO")
    print("="*70)
    
    print("\nQuery with 1 cue: ['food']")
    results = client.recall(["food"], limit=3)
    print(f"Found {len(results)} results")
    for r in results:
        print(f"  - {r.content[:50]}... (intersection: {r.intersection_count})")
    
    print("\nQuery with 2 cues: ['food', 'italian']")
    results = client.recall(["food", "italian"], limit=3)
    print(f"Found {len(results)} results")
    for r in results:
        print(f"  - {r.content[:50]}... (intersection: {r.intersection_count})")
    
    # Stats
    print("\n" + "="*70)
    print("STATISTICS")
    print("="*70)
    
    stats = client.stats()
    print(f"Total memories: {stats['total_memories']}")
    print(f"Total cues: {stats['total_cues']}")
    
    client.close()
    print("\n✓ Done!")


if __name__ == "__main__":
    main()
