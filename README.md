# DC-Simulator

The Idea of the workflow:
1. client.on_start() is called → it uses send() to send a request to the primary (e.g. Node 0)
2. Network.send() schedules a MESSAGE event (with a delay)
3. Simulator eventually delivers the event:
4. It calls primary_node.on_message(client_id, msg)
5. The primary processes the request and sends REPLICATE messages to backups.
6. Each backup receives the message, updates state, and sends ACK.
7. Primary collects ACKs, then replies to the client.
8. Client’s on_message() receives the reply and records latency.