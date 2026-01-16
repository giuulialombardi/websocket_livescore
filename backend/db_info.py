import os

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "livescore"
COLLECTION_NAME1 = "piloti"
COLLECTION_NAME2 = "gare"