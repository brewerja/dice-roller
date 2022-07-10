var stompClient;
var messagesClient;

var PLAYER_NAME_KEY = "playerName";

function connectRolls() {
	var socket = new SockJS('/roll');
	rollsClient = Stomp.over(socket);
	rollsClient.connect({}, function(frame) {
		rollsClient.subscribe('/topic/rolls/' + roomId, function(dieRoll) {
		    var d = JSON.parse(dieRoll.body);
			showRoll(d.name, d.timestamp, d.request, d.result);
		});
	});
}

function connectMessages() {
	var socket = new SockJS('/message');
	messagesClient = Stomp.over(socket);
	try {
		messagesClient.connect({}, function(frame) {
			messagesClient.subscribe('/topic/messages/' + roomId, function(message) {
			    var m = JSON.parse(message.body);
				showMessage(m.name, m.timestamp, m.message);
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

function showMessage(name, timestamp, message) {
	var ul = $('#rollContainer').find("ul").last();
    ul.find("li").last().attr("class", "list-group-item");
    ul.append(`<li class="list-group-item list-group-item-primary" title="${formatTimestamp(timestamp)}">
               <span class="me-2">${name}</span>
               <span>${message}</span>
               </li>`);
    scrollTop();
}

function showRoll(name, timestamp, request, result) {
	var ul = $('#rollContainer').find("ul").last();
    ul.find("li").last().attr("class", "list-group-item");
    ul.append(`<li class="list-group-item list-group-item-primary" title="${formatTimestamp(timestamp)}">
               <span class="me-2">${name}</span>
               <span class="badge bg-primary rounded-pill me-2">${request}</span>
               <span>${result}</span>
               </li>`);
    scrollTop();
}
