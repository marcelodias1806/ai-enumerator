# Policy Simulation and Feeds

AI Enumerator separates evidence collection from enforcement.

## Policy decisions

Catalog assets can move through review-oriented decisions such as allow, monitor, block, review or ignore according to the analyst workflow.

Automatic intelligence discovery never creates a block decision by itself.

## Simulation

Policy simulation estimates the effect of category decisions against measured exposure without changing network controls.

## Text feeds

Approved decisions can be exposed through generic text feeds for integration with downstream control systems.

Available feed families include:

- block-all
- GenAI web / coding
- AI API
- model distribution
- allow

Feed access is protected by the configured feed token.

## Operational workflow

```text
discover -> measure -> review -> simulate -> approve -> export feed -> rescan
```

After a network policy is changed, run a new exposure scan to validate the result from the relevant probe location.
