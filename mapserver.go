package main

import (
	"bytes"
	"code.google.com/p/go.net/websocket"
	"compress/zlib"
	"encoding/json"
	"fmt"
	zmq "github.com/alecthomas/gozmq"
	"io"
	"log"
	"net/http"
	"strconv"
)

var connections []*websocket.Conn

func main() {

	go relayListenerRoutine()

	http.Handle("/", websocket.Handler(handleWSConnection))
	err := http.ListenAndServe(":9000", nil)
	if err != nil {
		log.Fatal("%v", err)
	}
}

type Row []interface{}
type RowSet struct {
	Rows []Row
}
type Message struct {
	ResultType string
	RowSets    []RowSet
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
		emdrMsg, emdrErr := receiver.Recv(0)

		if emdrErr != nil {
			println("EMDR error:", emdrErr.Error())
		}
		msgReader := bytes.NewReader(emdrMsg)

		r, zl_rr := zlib.NewReader(msgReader)
		if zl_rr != nil {
			println("ZL ERROR:", zl_rr.Error())
		}

		var out bytes.Buffer
		io.Copy(&out, r)
		r.Close()
		//log.Printf("%s", out)

		var msg Message
		jsonErr := json.Unmarshal([]byte(out.String()), &msg)
		if jsonErr != nil {
			println("JSON ERROR:", jsonErr.Error())
		}

		if msg.ResultType != "orders" {
			continue
		}

		var sysIds []int
		systemsPresent := false
		for _, rowset := range msg.RowSets {
			for _, row := range rowset.Rows {
				sysidstr := fmt.Sprintf("%1.0f", row[10])
				sysid, _ := strconv.Atoi(sysidstr)
				sysIds = append(sysIds, sysid)
				systemsPresent = true
			}
		}
		if systemsPresent {
			//log.Println(sysIds)
		}
	}

}

func handleWSConnection(ws *websocket.Conn) {
	println("Connection!")
}
