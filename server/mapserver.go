package main

import (
	"code.google.com/p/go.net/websocket"
	"log"
	"net/http"
)

func main() {
	go h.run()
	go relayListenerRoutine()

	http.Handle("/", websocket.Handler(wsHandler))
	err := http.ListenAndServe(":9000", nil)
	if err != nil {
		log.Fatal("%v", err)
	}
}

func wsHandler(ws *websocket.Conn) {
	c := &connection{send: make(chan string, 256), ws: ws}
	h.register <- c
	defer func() { h.unregister <- c }()
	go c.writer()
	c.reader()
}
