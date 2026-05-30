import pandas as pd
import ast
from sklearn.feature_extraction.text import CountVectorizer
import pickle
import faiss
import numpy as np

def load_and_preprocess_data():
    # Load dataset
    movies = pd.read_csv('tmdb_5000_movies.csv')
    credits = pd.read_csv('tmdb_5000_credits.csv')

    # Merge dataset
    movies = movies.merge(credits, on='title')

    # Selecting relevant columns - including vote metrics and popularity for Hybrid approach
    base_movies = movies[['movie_id', 'title', 'overview', 'genres', 'keywords', 'cast', 'crew', 'vote_average', 'vote_count', 'popularity']].copy()

    # Drop missing values
    base_movies.dropna(inplace=True)

    # Helper functions to extract data
    def convert(text):
        L = []
        try:
            for i in ast.literal_eval(text):
                L.append(i['name']) 
        except:
            pass
        return L 

    def convert3(text):
        L = []
        counter = 0
        try:
            for i in ast.literal_eval(text):
                if counter < 3:
                    L.append(i['name'])
                    counter+=1
                else:
                    break
        except:
            pass
        return L 

    def fetch_director(text):
        L = []
        try:
            for i in ast.literal_eval(text):
                if i['job'] == 'Director':
                    L.append(i['name'])
                    break # Usually one director is enough
        except:
            pass
        return L 

    def collapse(L):
        return [i.replace(" ","") for i in L]

    # Applying the conversion functions
    base_movies['genres_list'] = base_movies['genres'].apply(convert)
    base_movies['keywords'] = base_movies['keywords'].apply(convert)
    base_movies['cast'] = base_movies['cast'].apply(convert3)
    base_movies['crew'] = base_movies['crew'].apply(fetch_director)

    base_movies['overview'] = base_movies['overview'].apply(lambda x:x.split())

    # Create a collapsed version for similarity but keep original for metadata display
    base_movies['cast'] = base_movies['cast'].apply(collapse)
    base_movies['crew'] = base_movies['crew'].apply(collapse)
    base_movies['genres_collapsed'] = base_movies['genres_list'].apply(collapse)
    base_movies['keywords_collapsed'] = base_movies['keywords'].apply(collapse)

    # Creating tags column for content similarity (using collapsed versions)
    base_movies['tags'] = base_movies['overview'] + base_movies['genres_collapsed'] + base_movies['keywords_collapsed'] + base_movies['cast'] + base_movies['crew']
    
    # Processed DataFrame for storage
    new_df = base_movies.copy()
    new_df['tags_string'] = new_df['tags'].apply(lambda x: " ".join(x).lower())
    new_df['genres'] = new_df['genres_list'] # Human readable

    # --- Weighted Rating Calculation (Hybrid component) ---
    # Formula: (v/(v+m) * R) + (m/(v+m) * C)
    v = new_df['vote_count']
    R = new_df['vote_average']
    C = new_df['vote_average'].mean()
    m = new_df['vote_count'].quantile(0.70) # Only movies with more than 70% of votes count

    new_df['weighted_score'] = (v/(v+m) * R) + (m/(v+m) * C)

    return new_df

def build_model(df):
    cv = CountVectorizer(max_features=5000, stop_words='english')
    # Use the string tags for vectorization
    vector = cv.fit_transform(df['tags_string']).toarray().astype('float32')
    
    # Normalizing vectors for Cosine Similarity using Inner Product Index
    faiss.normalize_L2(vector)
    
    # Building the FAISS index (IndexFlatIP = Inner Product, which is Cosine for normalized vectors)
    index = faiss.IndexFlatIP(5000)
    index.add(vector)
    
    return index, cv, vector

def hybrid_recommend(movie_title, df, index, top_n=5):
    try:
        # Get index of the movie
        idx = df[df['title'] == movie_title].index[0]
        
        # Reconstruct query vector from index
        query_vector = index.reconstruct(idx).reshape(1, -1)
        
        # Search the FAISS index for matches (fetching top_n + 1 to account for self)
        D, I = index.search(query_vector, top_n + 1)
        
        # Get matching movie indices, skipping self if present
        movie_indices = I[0]
        if idx in movie_indices:
            movie_indices = [i for i in movie_indices if i != idx]
        else:
            movie_indices = movie_indices[:top_n]
            
        recommendations = df.iloc[movie_indices].copy()
        recommendations = recommendations.sort_values('weighted_score', ascending=False)
        return recommendations.head(top_n)
    except IndexError:
        return "Movie not found in database."

if __name__ == "__main__":
    print("Preprocessing data and calculating weighted scores...")
    df = load_and_preprocess_data()
    print("Building scalable similarity index (FAISS)...")
    index, cv, vector = build_model(df)
    
    # Save data
    pickle.dump(df, open('movies_list.pkl', 'wb'))
    pickle.dump(cv, open('vectorizer.pkl', 'wb'))
    pickle.dump(vector, open('vectors.pkl', 'wb'))
    faiss.write_index(index, "movies_index.faiss")
    
    print("Model, vectorizer, index, and enhanced data saved.")

    # Example test
    test_movie = "Avatar"
    print(f"\nEvaluating performance for '{test_movie}'...")
    idx = df[df['title'] == test_movie].index[0]
    query_vector = vector[idx:idx+1]
    D, I = index.search(query_vector, 6) # Top 6 including self
    
    results = df.iloc[I[0][1:]] # Skip self
    print(f"Top matches via FAISS:")
    for m in results['title']:
        print(f"- {m}")
