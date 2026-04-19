"""
Local testing — search for movies without deploying.

Usage:
    python -m tests.test_local

Requires .env file with TMDB_API_KEY (and optionally OMDB_API_KEY).
"""

import sys
import os

# Add src to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Load .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

import movie_client


def main():
    print("=" * 60)
    print("🎬 קינומן — Local Test Mode")
    print("=" * 60)
    print()
    print("Type a movie name or 'quit' to exit.")
    print()

    while True:
        try:
            user_input = input("🎥 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nלהתראות! 👋")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("להתראות! 👋")
            break

        print("\n⏳ מחפש...\n")
        results = movie_client.search_movie(user_input)

        # If no direct match and looks like a description, use LLM to guess
        if not results and movie_client.is_description(user_input):
            print("🤔 לא מצאתי לפי שם, מנסה לזהות לפי תיאור...\n")
            guesses = movie_client.guess_movie_from_description(user_input)
            if guesses:
                print(f"💡 ניחושים: {', '.join(guesses)}\n")
            for guess in guesses:
                results = movie_client.search_movie(guess)
                if results:
                    break

        if not results:
            print("לא מצאתי סרט מתאים. נסה לתאר אחרת או לחפש בשם.")
            print()
            print("-" * 60)
            print()
            continue

        if len(results) == 1:
            choice = results[0]
        else:
            print("מצאתי כמה אפשרויות:")
            for i, r in enumerate(results[:5], 1):
                year = f" ({r['year']})" if r["year"] else ""
                print(f"  {i}. {r['title']} / {r['original_title']}{year}")
            print()
            try:
                pick = input("בחר מספר (או Enter לראשון): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nלהתראות! 👋")
                break
            idx = int(pick) - 1 if pick.isdigit() else 0
            idx = max(0, min(idx, len(results) - 1))
            choice = results[idx]

        print(f"\n⏳ טוען פרטים על {choice['title']}...\n")
        details = movie_client.get_movie_details(choice["id"])
        if details:
            print(movie_client.format_movie_response(details))
        else:
            print("לא הצלחתי לטעון פרטים על הסרט.")
        print()
        print("-" * 60)
        print()


if __name__ == "__main__":
    main()
