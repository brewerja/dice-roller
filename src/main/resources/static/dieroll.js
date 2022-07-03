var stompClient;
var messagesClient;

var PLAYER_NAME_KEY = "playerName";

function connectRolls() {
	var socket = new SockJS('/roll');
	rollsClient = Stomp.over(socket);
	rollsClient.connect({}, function(frame) {
		rollsClient.subscribe('/topic/rolls/' + roomId, function(dieRoll) {
			showRoll(JSON.parse(dieRoll.body).name,
					JSON.parse(dieRoll.body).timestamp,
					JSON.parse(dieRoll.body).request,
					JSON.parse(dieRoll.body).result);
		});
	});
}

function connectMessages() {
	var socket = new SockJS('/message');
	messagesClient = Stomp.over(socket);
	try {
		messagesClient.connect({}, function(frame) {
			messagesClient.subscribe('/topic/messages/' + roomId, function(dieRoll) {
				showMessage(JSON.parse(dieRoll.body).name, JSON
						.parse(dieRoll.body).message);
			});
		});
	} catch (e) {

	}

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
			initializeNames();
			addNameSaveHandlers();
			connectRolls();
			connectMessages();
		});

function roll(request) {
	name = $("#name").val();
	rollsClient.send("/app/roll/" + roomId, {}, JSON.stringify({
		'name' : name,
		'request' : request
	}));
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
	messagesClient.send("/app/message/" + roomId, {}, JSON.stringify({
		'name' : name,
		'message' : message,
	}));
	$("#message").val("");
}

function showMessage(name, message) {
	var response = document.getElementById('response');
	var dl;
	var lastRollerName;
	if ($(response).find("p").length > 0) {
		dl = $(response).find("p").last().find("dl").first();
		lastRollerName = dl.find("dt").first().text();
	}
	var dd = document.createElement('dd');

	dd.appendChild(document.createTextNode(message));

	if (lastRollerName == name) {
		dl.append(dd);
	} else {
		var p = document.createElement('p');
		p.style.wordWrap = 'break-word';
		var dl = document.createElement('dl');
		var dt = document.createElement('dt');
		dt.appendChild(document.createTextNode(name));

		dl.appendChild(dt);
		dl.appendChild(dd);
		p.appendChild(dl);
		response.appendChild(p);
	}
	var rollContainer = document.getElementById('rollContainer');
	rollContainer.scrollTop = rollContainer.scrollHeight;
}

function showRoll(name, timestamp, request, result) {
	var response = document.getElementById('response');
	var dl;
	var lastRollerName;
	if ($(response).find("p").length > 0) {
		dl = $(response).find("p").last().find("dl").first();
		lastRollerName = dl.find("dt").first().text();
	}
	var dd = document.createElement('dd');
	$(dd).css('font-style', 'italic');
	var myName = $('#name').val()
	requestString = request.split(",").map((n) => 'd' + n);
	var dateString = new Date(timestamp).toLocaleString('en-US', { hour12: true });
    dd.appendChild(document.createTextNode(dateString + " " + requestString + ' : ' + result));
	if (lastRollerName == name) {
		dl.append(dd);
	} else {
		var p = document.createElement('p');
		p.style.wordWrap = 'break-word';
		var dl = document.createElement('dl');
		var dt = document.createElement('dt');
		dt.appendChild(document.createTextNode(name));

		dl.appendChild(dt);
		dl.appendChild(dd);
		p.appendChild(dl);
		response.appendChild(p);
	}
	var rollContainer = document.getElementById('rollContainer');
	rollContainer.scrollTop = rollContainer.scrollHeight;
}