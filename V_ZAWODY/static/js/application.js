if (window.location.protocol == "https:") {
    var ws_scheme = "wss://";
} else {
    var ws_scheme = "ws://";
}

var inbox = new ReconnectingWebSocket(ws_scheme + location.host + "/receive");
var outbox = new ReconnectingWebSocket(ws_scheme + location.host + "/submit");

inbox.onmessage = function(message) {
    var data = JSON.parse(message.data);
    console.log('got data ' + data.id);
    $('#buttons #' + data.id).addClass('active');
};

$("#buttons a").on("click touch", function(event) {
    event.preventDefault();
    var button = $(this);
    var id = button.attr('id');
    console.log('activate ' + id);
    outbox.send(JSON.stringify({ id: id}));
    button.addClass('active');
});
