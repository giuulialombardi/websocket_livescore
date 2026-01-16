const raceId = window.location.pathname.split("/").pop();
const container = document.getElementById("container-gare");

function statoIconPilota(posizione) {
    return posizione;
}

function creaBoxPilota(pilota, posizione) {
    const box = document.createElement("div");
    box.className = "box-gara";
    box.id = `pilota-${pilota._id}`;

    box.innerHTML = `
        <p>
            <span class="posizione">${statoIconPilota(posizione)}</span>
            <span class="nome-pilota">${pilota.nome}</span>
        </p>
    `;
    return box;
}


function aggiornaClassifica(classifica, pilotiMap) {
    container.innerHTML = '';

    const posizioniOrdinate = Object.entries(classifica)
        .sort((a, b) => parseInt(a[0]) - parseInt(b[0]));

    posizioniOrdinate.forEach(([pos, pilotaId]) => {
        const pilota = pilotiMap[pilotaId];
        if (pilota) {
            const box = creaBoxPilota(pilota, pos);
            container.appendChild(box);
        }
    });
}

let pilotiGara = {};
async function caricaPiloti() {
    try {
        const res = await fetch(`/campionato-karting/api/piloti?race_id=${raceId}`);
        const data = await res.json();
        pilotiGara = {};
        data.piloti.forEach(p => pilotiGara[p._id] = p);

        Object.values(pilotiGara).forEach((p, i) => {
            const box = creaBoxPilota(p, i + 1);
            container.appendChild(box);
        });
    } catch (err) {
        console.error("Errore caricamento piloti:", err);
    }
}

const ws = new WebSocket("ws://localhost:8888/ws");

ws.onopen = () => {
    ws.send(JSON.stringify({ type: "subscribe", race_id: raceId }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.race_id !== raceId) return;

    if (data.type === "start" || data.type === "update" || data.type === "end") {
        const titolo = document.querySelector(".title");
        if (data.race_nome) titolo.textContent = data.race_nome;

        const infoItems = document.querySelectorAll(".info-item span:nth-child(2)");
        if (data.status) infoItems[0].textContent = data.status;

        if (data.classifica) {
            aggiornaClassifica(data.classifica, pilotiGara);
        }
    }
};

ws.onclose = () => console.warn("WebSocket chiuso");
ws.onerror = (err) => console.error("WebSocket errore:", err);

caricaPiloti();
