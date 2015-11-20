var stompClient = null;

function setConnected(connected) {
	document.getElementById('response').innerHTML = '';
}

function connectRolls() {
	var socket = new SockJS('/roll');
	stompClient = Stomp.over(socket);
	stompClient.connect({}, function(frame) {
		setConnected(true);
		console.log('Connected: ' + frame);
		stompClient.subscribe('/topic/rolls', function(dieRoll) {
			showRoll(JSON.parse(dieRoll.body).name, JSON.parse(dieRoll.body).numSides, JSON.parse(dieRoll.body).result,
					JSON.parse(dieRoll.body).privateRoll);
		});
	});
}

function connectMessages() {
	var socket = new SockJS('/message');
	stompClient = Stomp.over(socket);
	stompClient.connect({}, function(frame) {
		setConnected(true);
		console.log('Connected: ' + frame);
		stompClient.subscribe('/topic/messages', function(dieRoll) {
			showMessage(JSON.parse(dieRoll.body).name, JSON.parse(dieRoll.body).message);
		});
	});
}

$(document).ready(function connect() {
	connectRolls();
	connectMessages();
});

function makeName(name, charName) {
	return charName + ' (' + name + ')'
}

function disconnect() {
	if (stompClient != null) {
		stompClient.disconnect();
	}
	setConnected(false);
	console.log("Disconnected");
}

function roll(numSides) {
	name = $("#name").val();
	charName = $("#char").val();
	isPrivate = $('#isPrivate').prop('checked');
	stompClient.send("/app/roll", {}, JSON.stringify({
		'name' : makeName(name, charName),
		'numSides' : numSides,
		'privateRoll' : isPrivate
	}));
}

$(document).ready(function() {
	$("#message").keyup(function (e) {
	    if (e.keyCode == 13) {
	    	talk();
	    }
	});


});

function talk() {
	message = $("#message").val();
	name = $("#name").val();
	charName = $("#char").val();
	stompClient.send("/app/message", {}, JSON.stringify({
		'name' : makeName(name, charName),
		'message' : message,
	}));
	$("#message").val("");
}

var color_codes = {};
function stringToColorCode(str) {
	return (str in color_codes) ? color_codes[str] : (color_codes[str] = '#'
			+ ('000000' + (Math.random() * 0xFFFFFF << 0).toString(16)).slice(-6));
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
	var myName = $('#name').val()
	var myCharName = $('#char').val()
	
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
		p.style.color = stringToColorCode(name);
		response.appendChild(p);
	}
	var rollContainer = document.getElementById('rollContainer');
	rollContainer.scrollTop = rollContainer.scrollHeight;
}

function showRoll(name, numSides, result, isPrivate) {
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
	var myCharName = $('#char').val()
	if (!isPrivate) {
			dd.appendChild(document.createTextNode('d' + numSides + ' : ' + result));
	} else if (isPrivate && name == makeName(myName, myCharName)) {
		dd.appendChild(document.createTextNode('d' + numSides + ' : ' + result + ' (geheim)'));
	} else {
		dd.appendChild(document.createTextNode('geheimer Wurf'));
	}
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
		p.style.color = stringToColorCode(name);
		response.appendChild(p);
	}
	var rollContainer = document.getElementById('rollContainer');
	rollContainer.scrollTop = rollContainer.scrollHeight;
}