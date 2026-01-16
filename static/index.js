const container = document.getElementById("container-gare");
const gare = {};


function statoIcon(status) {
    if (status === "live") return "radio_button_checked";
    if (status === "terminata") return "check_circle";
    return "adjust";
}

function creaBoxGara(gara) {
    const box = document.createElement("div");
    box.className = "box-gara";
    box.id = `gara-${gara._id}`;

    box.innerHTML = `
        <p>
            <span class="material-symbols-outlined status-icon">${statoIcon(gara.status)}</span>
            <span class="status-text">${gara.status}</span>
            <span class="title-gara">${gara.nome}</span>
            <span class="material-symbols-outlined align-right" onclick="apriGara('${gara._id}')">
                open_in_full
            </span>
        </p>
    `;

    container.appendChild(box);
}


function aggiornaBoxGara(gara) {
    const box = document.getElementById(`gara-${gara._id}`);
    if (!box) return;

    const statusText = box.querySelector(".status-text");
    const statusIcon = box.querySelector(".status-icon");

    statusText.textContent = gara.status;
    statusIcon.textContent = statoIcon(gara.status);

}

function apriGara(raceId) {
    window.location.href = `/campionato-karting/${raceId}`;
}

async function caricaGare() {
    try {
        const res = await fetch("/campionato-karting/api");
        const data = await res.json();

        data.gare.forEach(g => {
            if (!gare[g._id]) {
                gare[g._id] = { nome: g.nome, status: g.status };
                creaBoxGara({ _id: g._id, ...gare[g._id] });
            } else {
                gare[g._id].status = g.status;
                aggiornaBoxGara({ _id: g._id, status: g.status });
            }
        });
    } catch (err) {
        console.error("Errore caricamento gare:", err);
    }
}

const ws = new WebSocket("ws://localhost:8888/ws");

ws.onopen = () => {
    ws.send(JSON.stringify({ type: "subscribe", race_id: null }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (!data.race_id && data.type !== "all_races_finished") return;

    if (data.type === "all_races_finished") {
        document.getElementById("btn-classifica").style.display = "inline-block";
        return;
    }

    if (!gare[data.race_id]) {
        gare[data.race_id] = {
            nome: data.nome || `Gara ${data.race_id.slice(-4)}`,
            status: data.type === "start" || data.type === "update" ? "live" :
                    data.type === "end" ? "terminata" :
                    "in programma"
        };
        creaBoxGara({ _id: data.race_id, ...gare[data.race_id] });
    } else {
        const stato = data.type === "start" || data.type === "update" ? "live" :
                      data.type === "end" ? "terminata" :
                      gare[data.race_id].status;
        gare[data.race_id].status = stato;
        aggiornaBoxGara({ _id: data.race_id, status: stato });
    }
};


ws.onclose = () => console.warn("WebSocket chiuso");
ws.onerror = (err) => console.error("WebSocket errore:", err);

async function mostraClassifica() {
    const container = document.getElementById("container-classifica");
    container.style.display = "block";
    container.innerHTML = "<p>Caricamento classifica...</p>";

    try {
        const res = await fetch("/campionato-karting/api/classifica");
        const data = await res.json();

        let html = "<h2>Classifica Finale</h2><ol>";
        data.classifica.forEach(p => {
            html += `<li class="classifica">${p.nome}: ${p.punteggio} punti</li>`;
        });
        html += "</ol>";

        container.innerHTML = html;
    } catch (err) {
        container.innerHTML = "<p>Errore caricamento classifica.</p>";
        console.error(err);
    }
}

caricaGare();
