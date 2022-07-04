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
			scrollTop();
			formatPriorRolls();
		});

function formatPriorRolls() {
    $('#rollContainer').find('li').each(function (i, v) {v.title = formatTimestamp(Number(v.title))});
}

function formatTimestamp(timestamp) {
	return new Date(timestamp).toLocaleString('en-US', { hour12: true });
}

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

function scrollTop() {
	var rollContainer = document.getElementById('rollContainer');
	rollContainer.scrollTop = rollContainer.scrollHeight;
}

function showMessage(name, message) {
	var ul = $('#rollContainer').find("ul").last();
	var li = document.createElement('li');
    li.appendChild(document.createTextNode(name + ": " + message));
    ul.append(li);
    scrollTop();
}

function showRoll(name, timestamp, request, result) {
	var ul = $('#rollContainer').find("ul").last();
	var li = document.createElement('li');
    li.appendChild(document.createTextNode(name + " " + request + ': ' + result));
    li.title = formatTimestamp(timestamp);
    li.setAttribute("class", "list-group-item active");
    ul.find("li").last().attr("class", "list-group-item");
    ul.append(li);
    scrollTop();
}
