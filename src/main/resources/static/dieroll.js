var stompClient;

var PLAYER_NAME_KEY = "playerName";

function connectRolls() {
	var socket = new SockJS('/roll');
	rollsClient = Stomp.over(socket);
	rollsClient.connect({}, function(frame) {
		rollsClient.subscribe('/topic/rolls/' + roomId, function(dieRoll) {
			showRoll(JSON.parse(dieRoll.body));
            scrollTop();
		});
	});
}

function initializeNames() {
	if(localStorage.getItem(PLAYER_NAME_KEY)) {
		$('#name').val(localStorage.getItem(PLAYER_NAME_KEY));
	}
}

function addNameSaveHandlers() {
	$('#name').change(function(){
		localStorage.setItem(PLAYER_NAME_KEY, $('#name').val());
	});
}

$(document).ready(
		function() {
            $.get(`/rooms/${roomId}/rolls`, showPriorRolls).done(scrollTop);
			initializeNames();
			addNameSaveHandlers();
			connectRolls();
		});

function showPriorRolls(rolls) {
  rolls.forEach(showRoll);
  var ul = $('#rollContainer').find("ul").last();
  ul.find("li").last().attr("class", "list-group-item list-group-item-secondary");
}

function formatTimestamp(timestamp) {
	return new Date(timestamp).toLocaleString('en-US', { hour12: true });
}

function roll(request) {
	name = $("#name").val();
	$.post({
	    url: "/rolls/" + roomId,
	    data: JSON.stringify({
            'name' : name,
		    'request' : request
	    }),
	    dataType: "json",
        contentType: "application/json; charset=utf-8"
	});
}

$(document).ready(function() {
	$("#message").keyup(function(e) {
		if (e.keyCode == 13) {
			talk();
		}
	});

});

function talk() {
	message = $("#message").val();
	name = $("#name").val();
	rollsClient.send("/app/roll/" + roomId, {}, JSON.stringify({
		'name' : name,
		'request' : message,
	}));
	$("#message").val("");
}

function scrollTop() {
	var rollContainer = document.getElementById('rollContainer');
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
    var ul = $('#rollContainer').find("ul").last();
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
