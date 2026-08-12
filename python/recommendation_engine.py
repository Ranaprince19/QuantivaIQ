import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import csr_matrix
from config import setup_logging
from utils import fetch_data

logger = setup_logging("RecommendationEngine")

class RecommendationEngine:
    def __init__(self):
        logger.info("Initializing Recommendation Engine...")

    def generate_recommendations(self):
        logger.info("Fetching purchase history for collaborative filtering...")
        query = """
            SELECT 
                o.customer_id,
                oi.product_id,
                SUM(oi.quantity) as purchase_count
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.status = 'Completed'
            GROUP BY o.customer_id, oi.product_id
        """
        df = fetch_data(query)
        if df.empty:
            logger.warning("No purchase history available for recommendations.")
            return

        # Create User-Item Matrix
        logger.info("Building User-Item interaction matrix...")
        user_item_matrix = df.pivot(index='customer_id', columns='product_id', values='purchase_count').fillna(0)
        
        # Sparse matrix conversion
        sparse_matrix = csr_matrix(user_item_matrix.values)

        # Compute Item-Item Cosine Similarity
        logger.info("Computing Item-Item similarities...")
        item_similarity = cosine_similarity(sparse_matrix.T)
        item_sim_df = pd.DataFrame(item_similarity, index=user_item_matrix.columns, columns=user_item_matrix.columns)

        # Let's generate recommendations for top 5 most active users as an example
        active_users = df['customer_id'].value_counts().head(5).index.tolist()
        
        for user in active_users:
            user_purchases = user_item_matrix.loc[user]
            bought_items = user_purchases[user_purchases > 0].index.tolist()
            
            if not bought_items:
                continue

            # Calculate score for each item based on similarity to bought items
            scores = item_sim_df[bought_items].sum(axis=1)
            # Remove already bought items
            scores = scores.drop(bought_items)
            
            top_5_recs = scores.nlargest(5).index.tolist()
            logger.info(f"Customer {user} recommendations: {top_5_recs}")

if __name__ == "__main__":
    recommender = RecommendationEngine()
    recommender.generate_recommendations()
