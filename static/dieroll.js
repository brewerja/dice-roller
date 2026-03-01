var PLAYER_NAME_KEY = "playerName";
var ws;

$(document).ready(
    function() {
        $.get(`/rooms/${roomId}/rolls`, showPriorRolls).done(scrollTop);
        initializeNames();
        addNameSaveHandlers();
        connectRolls();
        registerKeyboardCallbacks();
        $("#message").val("");
        $("#roll2d6").click(() => {roll("d6,d6")});
        $("#rolld20").click(() => {roll("d20")});
        $("#rolld6").click(() => {roll("d6")});
    });

function connectRolls(pendingSend) {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/${roomId}`);
    ws.onopen = function() {
        if (pendingSend) ws.send(pendingSend);
    };
    ws.onmessage = function(event) {
        showRoll(JSON.parse(event.data));
        scrollTop();
    };
    ws.onclose = function() {
        setTimeout(connectRolls, 1000);
    };
}

function send(data) {
    const msg = JSON.stringify(data);
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(msg);
    } else {
        connectRolls(msg);
    }
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
}

function showPriorRolls(rolls) {
    rolls.forEach(showRoll);
    $("#rollList").find("li").last().attr("class", "list-group-item list-group-item-secondary");
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
    const ul = $('#rollList');
    ul.find("li").last().attr("class", "list-group-item list-group-item-secondary");
    if (roll.results == null) {
        ul.append(`<li class="list-group-item list-group-item-primary" title="${formatTimestamp(roll.timestamp)}">
                       <span class="me-2">${roll.name}:</span>
                       <span>${roll.request}</span>
                   </li>`);
    } else {
        ul.append(`<li class="list-group-item list-group-item-primary" title="${formatTimestamp(roll.timestamp)}">
                       <span class="me-2">${roll.name}</span>
                       ${getRequestDisplay(roll.request, roll.results)}
                       <span class="fs-6 fst-italic">${roll.request}</span>
                   </li>`);
    }

}
