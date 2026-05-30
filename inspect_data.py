import pandas as pd
import ast

def load_data():
    movies = pd.read_csv('tmdb_5000_movies.csv')
    credits = pd.read_csv('tmdb_5000_credits.csv')
    return movies, credits

if __name__ == "__main__":
    movies, credits = load_data()
    print("Movies head:")
    print(movies.head())
    print("\nCredits head:")
    print(credits.head())
