# Distributed Agent Execution

This planning spec defines future distributed execution across multiple Worker Agents. It does not implement a scheduler, change the current database schema, or change Worker Agent runtime behavior.

## Current Runtime Boundary

The current preview runtime stores one `LoadTestTask`, selects one compatible idle `WorkerNode`, dispatches one worker request, and accepts one `TestResult` for that task. Future distributed execution should add explicit task run, shard, claim, and aggregation concepts instead of stretching the current one-task-one-worker shape.

## Core Concepts

| Concept | Definition |
|---|---|
| Logical task | User-facing test definition, such as "run payload profile for 1 hour with dataset users.csv". |
| Task run | One execution instance of a logical task. Retrying or rerunning creates a new task run. |
| Shard / sub-run | A partition of a task run assigned to one Worker Agent. A shard can carry its own execution bounds and dataset range. |
| Agent selector | Criteria used to match shards to eligible agents. |
| Agent labels | Operator-defined labels such as region, host group, network zone, engine availability, or target reachability. |
| Engine capability | Worker-advertised support for `k6`, `jmeter`, or future engines. |
| Target network reachability | A declared label or capability proving that an agent can reach the intended target network. |
| Dataset shard | Dataset partition assigned to a shard, such as offset 0 limit 2000. |
| Result shard | Per-shard result summary, raw report reference, artifacts, and stop metadata. |
| Artifact collection | Upload or reference collection for engine output, logs, and optional sample files. |

## Proposed Distribution Object

```json
{
  "distribution": {
    "mode": "sharded",
    "claim_model": "agent_claim",
    "agent_selector": {
      "engine": "k6",
      "labels": {
        "target_network": "internal-a"
      }
    },
    "shards": [
      {
        "shard_id": "users-a",
        "agent_selector": {
          "labels": {
            "target_network": "internal-a"
          }
        },
        "dataset_shard": {
          "offset": 0,
          "limit": 2000
        }
      },
      {
        "shard_id": "users-b",
        "agent_selector": {
          "labels": {
            "target_network": "internal-b"
          }
        },
        "dataset_shard": {
          "offset": 2000,
          "limit": 3000
        }
      }
    ]
  }
}
```

## Scheduling Model

Future distributed execution should use agent claim rather than Control Plane push:

1. Client creates a logical task with execution, distribution, and optional dataset objects.
2. Control Plane creates a task run and shard records.
3. Worker Agents poll or long-poll for claimable shards.
4. A Worker Agent claims one shard when its engine capability, labels, and target network reachability match.
5. The agent executes its shard and posts a result shard.
6. Control Plane aggregates shard status into the task run and logical task state.

This changes the future network direction: agents must reach the Control Plane, but the Control Plane does not need to connect directly to agent `/execute`. Target apps do not need to connect to the Control Plane.

## Agent Selector

Selector fields should be explicit and additive:

```json
{
  "agent_selector": {
    "engine": "k6",
    "labels": {
      "region": "tw",
      "target_network": "internal-a",
      "capacity_class": "medium"
    },
    "require_idle": true
  }
}
```

MVP matching should include engine capability and label equality. Future matching can add capacity scoring, resource thresholds, preferred agents, and exclusion rules.

## Dataset Partition Model

Dataset contract:

```json
{
  "dataset": {
    "source": "artifact://datasets/users.csv",
    "format": "csv",
    "partition_strategy": "manual_ranges",
    "shards": [
      {
        "shard_id": "users-a",
        "offset": 0,
        "limit": 2000
      },
      {
        "shard_id": "users-b",
        "offset": 2000,
        "limit": 3000
      }
    ]
  }
}
```

| Strategy | Meaning | MVP Status |
|---|---|---|
| `range` | Split a dataset into contiguous offset/limit ranges. | MVP candidate. |
| `manual` | Caller supplies explicit shard rows or shard identifiers. | MVP candidate for small datasets. |
| `manual_ranges` | Caller supplies explicit offset/limit ranges. | MVP candidate and recommended first implementation. |
| `hash` | Partition rows by hashing a stable key. | Future extension. |
| `weighted` | Split by agent weight or expected capacity. | Future extension. |
| `round_robin` | Assign alternating rows across shards. | Future extension. |

Dataset shard examples:

```json
{
  "shard_id": "users-a",
  "offset": 0,
  "limit": 2000,
  "labels": {
    "target_network": "internal-a"
  }
}
```

```json
{
  "shard_id": "users-b",
  "range": {
    "start_inclusive": 2000,
    "end_exclusive": 5000
  }
}
```

The MVP should not require the target app to know about Control Plane datasets. Workers should receive or resolve only the dataset shard needed for their run.

## Retry And Failure Behavior

Each shard should have its own lifecycle:

```text
pending -> claimed -> running -> completed
                         -> failed
                         -> cancelled
                         -> timed_out
```

Retry rules:

- A failed unstarted shard can be re-queued.
- A claimed shard whose heartbeat expires can be released after a lease timeout.
- A running shard that posts a failed result can be retried only if the dataset operation is idempotent or the caller explicitly allows retry.
- Retried shards must keep attempt numbers so duplicate result shards can be detected.

Partial success should be a first-class task run status when at least one shard completes and at least one shard fails, times out, or is cancelled.

## Cancellation Behavior

Cancellation should be propagated through shard state:

- Cancelling the logical task requests cancellation for all active shards.
- Agents should stop new traffic according to the shard stop policy.
- Graceful cancellation should wait for in-flight requests within the shard grace period.
- Force cancellation should be reserved for timeout or operator emergency paths.
- A cancelled shard still posts stop metadata and any available partial summary.

## Artifact Collection

Each result shard should carry artifact references:

```json
{
  "result_shard": {
    "shard_id": "users-a",
    "agent_id": "worker-a",
    "status": "completed",
    "artifacts": [
      {
        "kind": "k6-json",
        "uri": "artifact://runs/run-123/users-a/k6.jsonl"
      }
    ]
  }
}
```

The MVP can store small raw summaries inline and defer large raw reports to future artifact storage. Distributed percentile merging should not depend on inline raw reports unless size bounds are explicit.

## Distributed Result Aggregation

Aggregation rules:

- `total_requests` can be summed across result shards.
- `failed_requests` can be summed across result shards.
- Error rate should be recalculated from summed failures divided by summed requests.
- Throughput should be recalculated across a shared time window, not by summing or averaging shard RPS blindly.
- Average latency should not be calculated by directly averaging each agent average. Use request-count-weighted aggregation when only averages and counts are available.
- p95 and p99 should not be calculated by averaging shard p95 or p99 values.
- Correct percentile aggregation requires raw samples, histogram buckets, HDR histogram, t-digest, or engine-supported merge output.

MVP aggregation can expose:

- per-agent and per-shard summaries
- summed totals and failures
- recalculated global error rate
- conservative global summary with percentile fields marked as shard-level only unless mergeable data is available

Future aggregation should support histogram-based merge or engine-supported result merging.

## API And Dashboard Implications

Dashboard and API consumers should distinguish:

- logical task status
- task run status
- shard status
- aggregate result status
- per-shard result status

The dashboard should show partial success explicitly and avoid presenting unmergeable percentiles as global truth.

## Contract Status

This is a planning contract. The first implementation should add API contract tests before enabling runtime distributed scheduling.
