#!/usr/bin/env python3
"""Route/device health probe — the matched control used in `results/h_embed_outcome.md`.

Submits the smallest possible real job (1 qubit, 1 gate, 100 shots) to one device and polls to a
600 s ceiling. A device that cannot return that circuit within ten minutes while advertising
`ONLINE, queue_depth: 0` is not busy — it is not accepting work, and no amount of waiting helps.

Run it against two devices on the SAME route to separate a broken route from a broken device. That
is exactly how we withdrew our own (too broad) "the OpenQuantum route's dispatch layer is down"
attribution on 2026-07-26:

    python3 route_health_probe.py openquantum:rigetti:qpu:cepheus-1-108q   # COMPLETED in 182 s
    python3 route_health_probe.py openquantum:iqm:qpu:garnet               # not terminal at 600 s

Cost is negligible (100 shots; free on the OpenQuantum route), so this is cheap enough to run
before committing a funded campaign to a device. Requires QBRAID_API_KEY in the environment.

Exit codes:  0 = terminal (device answered)   1 = not terminal within the ceiling   2 = error
"""
import datetime
import sys
import time

CEILING_S = 600
POLL_S = 15
SHOTS = 100

# X|0> = |1>: a correct device returns ~100% '1', so the probe also validates the answer, not just
# the fact that something came back.
QASM = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\ncreg c[1];\nx q[0];\nmeasure q -> c;\n'


def probe(device_id, ceiling_s=CEILING_S):
    from qbraid.runtime import QbraidProvider

    device = QbraidProvider().get_device(device_id)
    meta = device.metadata()
    print(f"{device_id}  advertised status={device.status().name}  "
          f"queue_depth={meta.get('queue_depth')}", flush=True)

    t0 = time.time()
    job = device.run(QASM, shots=SHOTS, tags={"purpose": "route-health-probe"})
    print(f"submitted {job.id} at {datetime.datetime.now(datetime.timezone.utc):%H:%M:%S} UTC",
          flush=True)

    last = None
    while time.time() - t0 < ceiling_s:
        status = job.status()
        if status != last:
            print(f"  [{time.time() - t0:6.0f}s] {status}", flush=True)
            last = status
        if status.name in ("COMPLETED", "FAILED", "CANCELLED"):
            print(f"TERMINAL: {status.name} after {time.time() - t0:.0f} s", flush=True)
            if status.name == "COMPLETED":
                print(f"counts: {job.result().data.get_counts()}", flush=True)
            return 0
        time.sleep(POLL_S)

    print(f"NOT TERMINAL after {ceiling_s} s -- status {job.status()}", flush=True)
    print("The device is not accepting work, regardless of what its status field advertises.",
          flush=True)
    return 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"usage: {sys.argv[0]} <qbraid-device-id>\n"
                 f"  e.g. {sys.argv[0]} openquantum:iqm:qpu:garnet")
    try:
        sys.exit(probe(sys.argv[1]))
    except Exception as exc:                                  # noqa: BLE001 - report, don't mask
        print(f"probe error: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)
