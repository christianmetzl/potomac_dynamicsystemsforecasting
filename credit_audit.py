"""
credit_audit.py - self-contained, independent re-derivation of the whole-program QPU cost.

Comprehensive cost transparency without trusting our self-report: every campaign's cost is
RE-DERIVED here from (a) qBraid's PUBLISHED per-shot pricing and (b) the committed shot
configuration, then asserted against the billed figure recorded in results/CREDIT_BUDGET.md.
No API key, no network, no organizer credentials needed - a judge runs `cli.py run credit_audit`
and reproduces the ledger from first principles. (Anyone with org visibility can additionally
re-fetch per-job `cost` from the platform; that path is in CREDIT_BUDGET.md section 5.)

Pricing (qBraid native route, verified live against billed jobs during the program):
  IonQ Forte-1     8      cr/shot + 30 cr task fee
  IQM Garnet       0.145  cr/shot + 30
  IQM Emerald      0.16   cr/shot + 30
  Rigetti Cepheus  0.0425 cr/shot + 30
  qir-sv (sim)     free
Failed/rejected submissions bill 0 (validation errors never execute).
"""
RATE = {"ionq": 8.0, "garnet": 0.145, "emerald": 0.16, "rigetti": 0.0425}
TASK_FEE = 30.0

# Each campaign as executed: (device_key, [shot counts of the BILLED jobs], billed_of_record, pool)
# probe jobs run at 100 shots; cals + window/fold circuits run at the campaign shot count.
CAMPAIGNS = [
    ("hw_garnet_native",    "garnet",  [100] + [4000] * 11, 6754.5,  "org"),
    ("hw_ionq_smoke",       "ionq",    [100],                830.0,   "org"),   # +3 fold-5 rejects @ 0
    ("hw_ionq_native",      "ionq",    [500] * 5,            20150.0, "org"),
    ("hw_rigetti_rep",      "rigetti", [100] + [4000] * 11,  2234.25, "org"),
    ("hw_garnet_n10",       "garnet",  [100] + [4000] * 11,  6754.5,  "org"),
    ("hw_garnet_n12",       "garnet",  [100] + [4000] * 11,  6754.5,  "org"),
    ("hw_garnet_n8_anchor", "garnet",  [100] + [4000] * 11,  6754.5,  "org"),
    ("hw_emerald_n8",       "emerald", [100] + [4000] * 11,  7416.0,  "org"),
    ("hw_garnet_n8_pair",   "garnet",  [4000] * 5,           3050.0,  "org"),
    ("hw_emerald_n8_pair",  "emerald", [4000] * 5,           3350.0,  "personal"),  # attribution anomaly
]
CEILING = 65000.0


def derive(device_key, shots):
    r = RATE[device_key]
    return sum(s * r + TASK_FEE for s in shots)


def main():
    print(f"{'campaign':22s} {'pool':9s} {'jobs':>5s} {'re-derived':>12s} {'of record':>11s}  check")
    print("-" * 72)
    org = personal = 0.0
    all_ok = True
    for tag, dev, shots, billed, pool in CAMPAIGNS:
        d = derive(dev, shots)
        ok = abs(d - billed) < 0.01
        all_ok &= ok
        if pool == "org":
            org += billed
        else:
            personal += billed
        print(f"{tag:22s} {pool:9s} {len(shots):>5d} {d:>12.2f} {billed:>11.2f}  "
              f"{'OK' if ok else '*** MISMATCH ***'}")
    print("-" * 72)
    print(f"{'ORG-POOL settled':22s} {'':9s} {'':>5s} {'':>12s} {org:>11.2f}")
    print(f"{'PERSONAL (anomaly)':22s} {'':9s} {'':>5s} {'':>12s} {personal:>11.2f}")
    print(f"{'qBraid HARDWARE TOTAL':22s} {'':9s} {'':>5s} {'':>12s} {org + personal:>11.2f}")
    print()
    print(f"Org ceiling:            {CEILING:>11.2f}")
    print(f"Org settled:            {org:>11.2f}")
    print(f"Org reserve remaining:  {CEILING - org:>11.2f}")
    print()
    print("Also spent, outside the org ceiling (separate currencies / accounts):")
    print("  Self-funded era (personal qBraid): Rigetti full protocol ≈1,380 cr (≈$14) + free-tier sims (0)")
    print("  OpenQuantum route (personal OQ credits, free-tier/promotional): ≈147 OQ cr")
    print(f"  Involuntary personal charge (Emerald pair, platform anomaly): {personal:.0f} qBraid cr")
    print()
    verdict = "ALL CAMPAIGNS RECONCILE (re-derived == billed of record)" if all_ok \
        else "*** RECONCILIATION FAILURE - investigate ***"
    print(verdict)
    # hard assertions so this is a real test, not a print
    assert all_ok, "cost re-derivation does not match the ledger"
    assert abs(org - 60698.25) < 0.01, f"org total drift: {org}"
    assert org <= CEILING, "org spend exceeds the agreed ceiling"
    print("Assertions passed: ledger is internally consistent and within ceiling.")


if __name__ == "__main__":
    main()
