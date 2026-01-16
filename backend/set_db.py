from pymongo import AsyncMongoClient
import json, asyncio, random, db_info, os

lista_gruppi = [1]*8 + [2]*8 + [3]*8 + [4]*8 + [5]*8 + [6]*8 + [7]*8 + [8]*8 + [9]*8 + [10]*8

class gestione_db:
    def __init__(self):
        self.client = AsyncMongoClient(db_info.MONGO_URL)
        self.db = self.client[db_info.DB_NAME]
        self.piloti = self.db[db_info.COLLECTION_NAME1]
        self.gare = self.db[db_info.COLLECTION_NAME2]
        self.gruppi = lista_gruppi

    async def set_db(self):
        cont1= await self.piloti.count_documents({})
        cont2 = await self.gare.count_documents({})
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        if cont1 == 0:
            pilot_path = os.path.join(backend_dir, "pilots.json")
            with open(pilot_path) as f:
                data = json.load(f)
            await self.piloti.insert_many(data)
        if cont2==0:
            races_path = os.path.join(backend_dir, "races.json")
            with open(races_path) as f:
                data = json.load(f)
            await self.gare.insert_many(data)

    async def reset_db(self):
        await self.piloti.update_many({},{"$set": {"status": 1, "punteggio": 0, "penalita": 0, "gruppo": 0, "classifica": 0, "posizione": 0}})
        await self.gare.update_many({},{"$set":{"status": "in programma","classifica":{}}})

    async def set_groups(self):
        gruppi = self.gruppi.copy()
        cursor = self.piloti.find({})
        random.shuffle(gruppi)
        async for pilota in cursor:
            gruppo = gruppi.pop(random.randrange(len(gruppi)))
            await self.piloti.update_one(
                {"_id": pilota["_id"]},
                {"$set": {"gruppo": gruppo}}
            )


async def main():
    gestione=gestione_db()
    await gestione.set_db()
    await gestione.reset_db()
    await gestione.set_groups()


if __name__ == "__main__":
    asyncio.run(main())