package main

import (
	"bytes"
	"compress/zlib"
	"encoding/json"
	zmq "github.com/alecthomas/gozmq"
	"io"
	"log"
)

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
				sysId := int(row[10].(float64))
				sysIds = append(sysIds, sysId)
				systemsPresent = true
			}
		}
		if systemsPresent {
			sJson, _ := json.Marshal(sysIds)
			log.Printf("%s", sJson)
			h.broadcast <- string(sJson)
		}
	}

}
