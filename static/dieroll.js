var PLAYER_NAME_KEY = "playerName";
var ws;
var lastPongTime = Date.now();
var heartbeatInterval;
var reconnectTimer = null;
var pendingMessages = [];
var displayedRolls = new Set();
var roomTitle = document.title;
var unseenRolls = 0;

$(document).ready(
    function() {
        initializeNames();
        addUnseenRollCount();
        addNameSaveHandlers();
        connectRolls();
        registerKeyboardCallbacks();
        $("#message").val("");
        $("#roll2d6").click(() => {roll("d6,d6")});
        $("#rolld20").click(() => {roll("d20")});
        $("#rolld6").click(() => {roll("d6")});
    });

// Only one socket is ever current. Opening a new one closes the old one, and
// every handler ignores events from a socket that is no longer current.
function connectRolls() {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
    clearInterval(heartbeatInterval);
    if (ws) {
        ws.onclose = null;
        ws.close();
        showStatus("reconnecting");
    }
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const socket = new WebSocket(`${protocol}//${window.location.host}/ws/${roomId}`);
    ws = socket;
    socket.onopen = function() {
        if (socket !== ws) return;
        lastPongTime = Date.now();
        $.get(`/rooms/${roomId}/rolls`, function(rolls) {
            rolls.forEach(showRoll);
            scrollTop();
        });
        while (pendingMessages.length) socket.send(pendingMessages.shift());
        showStatus("connected");
        heartbeatInterval = setInterval(function() {
            if (Date.now() - lastPongTime > 10000) {
                // Don't wait on close(): a dead connection can take a long time to finish closing.
                connectRolls();
            } else {
                socket.send(JSON.stringify({type: 'ping'}));
            }
        }, 5000);
    };
    socket.onmessage = function(event) {
        if (socket !== ws) return;
        lastPongTime = Date.now();
        const data = JSON.parse(event.data);
        if (data.pong) return;
        if (showRoll(data) && document.hidden) {
            unseenRolls++;
            document.title = `(${unseenRolls}) ${roomTitle}`;
        }
        scrollTop();
    };
    socket.onclose = function() {
        if (socket !== ws) return;
        showStatus("reconnecting");
        clearInterval(heartbeatInterval);
        if (reconnectTimer === null) reconnectTimer = setTimeout(connectRolls, 1000);
    };
}

// Messages sent while disconnected are queued and sent once the socket opens.
function send(data) {
    const msg = JSON.stringify(data);
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(msg);
        return;
    }
    pendingMessages.push(msg);
    if (ws.readyState !== WebSocket.CONNECTING) connectRolls();  // reconnect now rather than waiting for the timer
    showStatus("reconnecting");
}

// The dot's color alone is easy to miss and only explained in a tooltip, so
// say in words when not connected, including how many messages are waiting.
function showStatus(state) {
    const waiting = pendingMessages.length ? ` (${pendingMessages.length} waiting to send)` : "";
    const [cls, text] = {
        connected: ["text-success", ""],
        reconnecting: ["text-danger", "Reconnecting…" + waiting],
    }[state];
    $("#connStatus").attr("class", cls).attr("title", text || "Connected");
    $("#connText").attr("class", `${cls} small`).toggleClass("d-none", !text).text(text);
}

function initializeNames() {
    if (localStorage.getItem(PLAYER_NAME_KEY)) {
        $('#name').val(localStorage.getItem(PLAYER_NAME_KEY));
    }
}

function addNameSaveHandlers() {
    $('#name').change(function(){
        localStorage.setItem(PLAYER_NAME_KEY, $('#name').val());
    });
    $('#name').on('input', () => markMyRolls($('#rollList li')));
}

function formatTimestamp(timestamp) {
    return new Date(timestamp).toLocaleString('en-US', { hour12: true });
}

function roll(request) {
    send({'name': $("#name").val(), 'request': request});
}

var n = 0

function registerKeyboardCallbacks() {
    $("body").keyup(function(e) {
        if (e.target.type === "text") {
            return;
        }
        if (e.keyCode == 82) { // 'R'
            roll("d6,d6");
        } else if (e.keyCode == 66) { // 'B'
            roll("d20");
        } else if (e.keyCode == 71) { // 'G'
            roll("d6");
        }
    });
    $("#message").keyup(function(e) {
        if (e.keyCode == 13) {
            talk();
            n = 0;
        } else if (e.keyCode == 38) {
            $("#message").val("");
            n = Math.max(-100, n - 1);
            const lastRequest = $("#rollList").find("li").eq(n).find("span").last().text();
            $("#message").val(lastRequest);
        } else if (e.keyCode == 40) {
            n = Math.min(0, n + 1);
            $("#message").val("");
            if (n != 0) {
                const lastRequest = $("#rollList").find("li").eq(n).find("span").last().text();
                $("#message").val(lastRequest);
            }
        }
    });
}

function talk() {
    const message = $("#message").val();
    if (message == "")
        return
    send({'name': $("#name").val(), 'request': message});
    $("#message").val("");
}

function scrollTop() {
    const rollContainer = document.getElementById('rollContainer');
    rollContainer.scrollTop = rollContainer.scrollHeight;
}

function getRequestDisplay(request, results) {
    if (request == "d20")
        return `<span class="badge text-bg-primary me-2">${results[0]}</span>`
    else if (request == "d6,d6") {
        return `<span class="badge text-bg-danger me-2">${results[0]}</span><span class="badge text-bg-light me-2">${results[1]}</span>`
    } else if (request == "d6")
        return `<span class="badge text-bg-success me-2">${results[0]}</span>`
    else {
        return results.map(n => `<span class="badge text-bg-secondary me-2">${n}</span>`).join("");
    }
}

function showRoll(roll) {
    // Rolls saved before IDs were added only have a timestamp to tell them apart.
    const key = roll.id ?? roll.timestamp;
    if (displayedRolls.has(key)) return false;
    displayedRolls.add(key);
    const ul = $('#rollList');
    ul.find("li").last().removeClass("list-group-item-primary").addClass("list-group-item-secondary");
    let li;
    if (roll.results == null) {
        li = $(`<li class="list-group-item list-group-item-primary" title="${formatTimestamp(roll.timestamp)}">
                    <span class="me-2">${roll.name}:</span>
                    <span>${roll.request}</span>
                </li>`);
    } else {
        li = $(`<li class="list-group-item list-group-item-primary" title="${formatTimestamp(roll.timestamp)}">
                    <span class="me-2">${roll.name}</span>
                    ${getRequestDisplay(roll.request, roll.results)}
                    <span class="fs-6 fst-italic">${roll.request}</span>
                </li>`);
    }
    // The server escapes names (& becomes &amp;), so compare the name as text.
    li.attr("data-name", new DOMParser().parseFromString(roll.name, "text/html").body.textContent);
    ul.append(li);
    markMyRolls(li);
    return true;
}

// While the tab is in the background, the title counts rolls that arrived, e.g. "(3) red — Rolling Room".
function addUnseenRollCount() {
    document.addEventListener("visibilitychange", function() {
        if (document.hidden) return;
        unseenRolls = 0;
        document.title = roomTitle;
    });
}

// Rolls made under the name in the name box get a colored edge.
function markMyRolls(rows) {
    const me = $("#name").val();
    rows.each(function() {
        $(this).toggleClass("mine", me !== "" && $(this).attr("data-name") === me);
    });
}
