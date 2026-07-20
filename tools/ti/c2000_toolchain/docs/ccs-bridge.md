# CCS bridge protocol

The bridge uses line-delimited JSON on stdin and tagged line-delimited JSON on
stdout. Tagged output starts with `@@C2000@@`; untagged CCS output is forwarded to
the VS Code Debug Console rather than being parsed as protocol data.

Request:

```json
{"id":1,"method":"registers","params":{"coreId":1}}
```

Successful response:

```json
{"id":1,"ok":true,"result":{"registers":[{"name":"PC","value":"4660","bits":32}]}}
```

Event:

```json
{"event":"stopped","coreId":1,"reason":"breakpoint"}
```

Big integers cross the protocol as decimal strings. The schema is in
`bridge/protocol.schema.json`.
