# Scanning Methodology

AI Enumerator performs controlled outbound reachability validation against destinations in the intelligence catalog.

## Measurement sequence

For each target:

```text
DNS -> TCP/443 -> TLS -> HTTP
```

The scanner records technical evidence such as resolution state, transport connectivity, TLS completion, HTTP response status and latency.

## Status interpretation

- **reachable**: HTTP responded.
- **partial**: transport/TLS evidence exists but HTTP did not fully complete.
- **blocked**: DNS resolved but TCP connectivity was unavailable/blocked.
- **failed**: DNS or another transport-stage error prevented useful evidence.

An HTTP 401, 403 or 404 can still prove egress reachability because a remote HTTP service answered.

## What a scan proves

A scan proves reachability from the selected probe/network location.

It does not prove:

- an employee used the service;
- authentication succeeded;
- an inference API call would succeed;
- prompts were sent;
- model files were downloaded.

## Probe placement

Different networks can have different egress policies. Deploy probes in relevant segments if you need to compare office, datacenter, VPN, cloud, lab or other network paths.

## Repeated scans

Run scans before and after egress-policy changes. Assessment history can then show whether endpoints became reachable, unreachable or changed state.
