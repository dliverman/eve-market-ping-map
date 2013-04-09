package main

import (
	"code.google.com/p/go.net/websocket"
	zmq "github.com/alecthomas/gozmq"
	"log"
	"net/http"
)

func main() {

	go relayListenerRoutine()

	http.Handle("/websocket/", websocket.Handler(handleWSConnection))
	err := http.ListenAndServe(":9000", nil)
	if err != nil {
		log.Fatal("%v", err)
	}
}

func relayListenerRoutine() {
	context, _ := zmq.NewContext()

	receiver, _ := context.NewSocket(zmq.SUB)
	receiver.SetSockOptString(zmq.SUBSCRIBE, "")
	//receiver.Connect("tcp://master.eve-emdr.com:8050")
	receiver.Connect("tcp://secondary.eve-emdr.com:8050")
	//receiver.Connect("tcp://relay-us-central-1.eve-emdr.com:8050")

	println("Listening on port 8050...")

	for {
		msg, zmq_err := receiver.Recv(0)

		if zmq_err != nil {
			println("RECV ERROR:", zmq_err.Error())
		}

		println("%v", msg)
		//sender.Send(msg, 0)

	}

}

func handleWSConnection(ws *websocket.Conn) {
	go wsConnectionEchoRoutine(ws)
}

func wsConnectionEchoRoutine(ws *websocket.Conn) {

}
