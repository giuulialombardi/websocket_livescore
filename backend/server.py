import asyncio, json, logging, tornado.web, tornado.websocket, db_info, random, set_db, os
from pymongo import AsyncMongoClient
from bson import ObjectId

time=1
lap_time=5
clients={}
PUNTI = [25, 21, 17, 14, 12, 10, 8, 6, 4, 2]

async def aggiorna_punteggio(self):
    piloti_ordinati = sorted(self.piloti, key=lambda p: p.posizione)
    for i, pilota in enumerate(piloti_ordinati):
        punti = PUNTI[i] if i < len(PUNTI) else 0
        await piloti.update_one(
            {"_id": pilota.id},
            {"$inc": {"punteggio": punti}}
        )


client = AsyncMongoClient(db_info.MONGO_URL)
db = client[db_info.DB_NAME]
piloti = db[db_info.COLLECTION_NAME1]
gare = db[db_info.COLLECTION_NAME2]

def broadcast(message):
    for client, race_id in clients.items():
        try:
            if race_id is None or race_id==message["race_id"]:
                logging.info("invio messaggio")
                client.write_message(json.dumps(message))
        except Exception as e:
            logging.error("errore invio", e)


class Pilota:
    def __init__(self, pilota_doc):
        self.velocita = random.uniform(0.95, 1.05)
        self.tempo = 0.0
        self.posizione = pilota_doc['posizione']
        self.id = pilota_doc['_id']


class Race:
    def __init__(self, piloti, race, doc_races):
        self.piloti = [Pilota(p) for p in piloti]
        self.race = race
        self.doc_races = doc_races

    async def run(self):
        self.init_classifica()
        broadcast({
            "type": "start",
            "race_id": str(self.race["_id"]),
            "status": "live",
            "lap": 0,
            "classifica": self.race["classifica"]
        })
        for giro in range(1, self.race["laps"]+1):
            for pilota in self.piloti:
                self.giro(pilota)
            self.aggiorna_classifica()
            broadcast({
                "type": "update",
                "race_id": str(self.race["_id"]),
                "status": "live",
                "lap": giro,
                "classifica": self.race["classifica"]
            })
            await asyncio.sleep(lap_time * time)
        await self.doc_races.update_one({"_id":self.race["_id"]}, {"$set":{"classifica":self.race["classifica"], "status": "terminata"}})
        broadcast({
            "type": "end",
            "race_id": str(self.race["_id"]),
            "status": "terminata",
            "lap": self.race["laps"],
            "classifica": self.race["classifica"]
        })
        await self.aggiorna_punteggio()
        await asyncio.sleep(1*time)

    async def aggiorna_punteggio(self):
        piloti_ordinati = sorted(self.piloti, key=lambda p: p.posizione)
        for i, pilota in enumerate(piloti_ordinati):
            punti = PUNTI[i] if i < len(PUNTI) else 0
            await piloti.update_one(
                {"_id": pilota.id},
                {"$inc": {"punteggio": punti}}
            )


    def init_classifica(self):
        classifica={}
        random.shuffle(self.piloti)
        for i, pilota in enumerate(self.piloti):
            pilota.posizione = i+1
            classifica[str(pilota.posizione)]=str(pilota.id)
        #print(classifica)
        self.race["classifica"]=classifica


    def aggiorna_classifica(self):
        classifica={}
        piloti_ordinati = sorted(self.piloti, key=lambda p: p.tempo)
        for i, pilota in enumerate(piloti_ordinati):
            pilota.posizione = i+1
            classifica[str(pilota.posizione)] = str(pilota.id)
        #print(classifica)
        self.race["classifica"]=classifica


    def giro(self, pilota):
        variazione = random.uniform(0.90, 1.10)
        giro_pilota = lap_time * pilota.velocita * variazione
        pilota.tempo += giro_pilota


class Scheduler:
    def __init__(self):
        self.client = client
        self.db = db
        self.piloti = piloti
        self.gare = gare

    async def run(self):
        for _ in range(9):
            tasks=[]
            #print("inizio turno")
            for _ in range(5):
                race=await self.gare.find_one_and_update({"status":"in programma"}, {"$set":{"status":"live"}}, sort=[("_id", 1)], return_document=True)
                if not race:
                    #print("finite le gare")
                    break
                else:
                    gruppi = race.get("gruppi", [])
                    #print(gruppi)
                    piloti_gruppi = await self.piloti.find({"gruppo": {"$in": gruppi}}).to_list(None)
                    #print(piloti_gruppi)
                    race_attiva=Race(piloti_gruppi, race, self.gare)
                    tasks.append(asyncio.create_task(race_attiva.run()))
            await asyncio.gather(*tasks)
            #print("fine turno")
            await asyncio.sleep(1*time)
        remaining = await self.gare.count_documents({"status": {"$in": ["in programma", "live"]}})
        if remaining == 0:
            print("Tutte le gare sono terminate, invio segnale classifica finale")
            broadcast({"type": "all_races_finished"})


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")

class DetailHandler(tornado.web.RequestHandler):
    async def get(self, race_id):
        race = await gare.find_one({"_id": ObjectId(race_id)})
        if race:
            nome = race.get("nome", f"Gara {race_id[-4:]}")
            circuito = race.get("circuito", "")
            status = race.get("status", "in programma")
            laps = race.get("laps", 0)
        else:
            nome = f"Gara {race_id[-4:]}"
            circuito = ""
            status = "in programma"
            laps = 0

        await self.render("detail.html", nome_gara=nome, circuito=circuito, status=status, laps=laps, race_id=race_id)

class APIHandler(tornado.web.RequestHandler):
    async def get(self):
        races = await gare.find().sort("_id", 1).to_list(None)
        info = []
        for r in races:
            info.append({
                "_id": str(r["_id"]),
                "nome": r.get("nome", f"Gara {str(r['_id'])[-4:]}"),
                "status": r.get("status")
            })
        self.write({"gare": info})


class PilotiAPIHandler(tornado.web.RequestHandler):
    async def get(self):
        race_id = self.get_argument("race_id")
        race = await gare.find_one({"_id": ObjectId(race_id)})
        if not race:
            self.write({"piloti": []})
            return
        gruppi = race.get("gruppi", [])
        piloti_gara = await piloti.find({"gruppo": {"$in": gruppi}}).to_list(None)
        # ritorna solo _id e nome
        result = [{"_id": str(p["_id"]), "nome": p.get("nome", f"Pilota {str(p['_id'])[-4:]}")} for p in piloti_gara]
        self.write({"piloti": result})


class ClassificaFinaleAPIHandler(tornado.web.RequestHandler):
    async def get(self):
        top_piloti = await piloti.find().sort("punteggio", -1).to_list(None)
        result = [
            {"_id": str(p["_id"]), "nome": p.get("nome", f"Pilota {str(p['_id'])[-4:]}"), "punteggio": p.get("punteggio", 0)}
            for p in top_piloti
        ]
        self.write({"classifica": result})


class WSHandler(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        print("WebSocket aperto")
        self.race_id=None
        clients[self]=None

    def on_message(self, message):
        data = json.loads(message)
        if data["type"] == "subscribe":
            self.race_id = data["race_id"]
            clients[self] = data["race_id"]

    def on_close(self):
        print("WebSocket chiuso")
        clients.pop(self, None)


async def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = tornado.web.Application(
        [
            (r"/campionato-karting", IndexHandler),
            (r"/campionato-karting/api", APIHandler),
            (r"/campionato-karting/api/piloti", PilotiAPIHandler),
            (r"/ws", WSHandler),
            (r"/campionato-karting/api/classifica", ClassificaFinaleAPIHandler),
            (r"/campionato-karting/([0-9a-fA-F]{24})", DetailHandler)
        ],
        template_path=os.path.join(project_root, "templates"),
        static_path=os.path.join(project_root, "static")
    )

    app.listen(8888)
    print("Server Tornado avviato su http://localhost:8888/campionato-karting")

    await set_db.main()
    await asyncio.sleep(5)
    scheduler = Scheduler()
    asyncio.create_task(scheduler.run())
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

