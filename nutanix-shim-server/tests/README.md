# nutanix-shim-server tests

Run from `nutanix-shim-server/`: `uv run pytest` (or `pytest` inside the venv).

## Covered

- `utils.paginate` — multi-page accumulation, single page, empty/`None` data,
  absent metadata/links, the missing-`last`-link case, the absent page cap.
- `utils.retry_on_timeout` — first-try success, retry after one
  `ReadTimeoutError`/`MaxRetryError`, both attempts failing, objects with and
  without a `_clear_clients` hook, non-timeout errors not retried.
- `utils.configure_sdk` / `add_default_headers` — against a fake config and
  the real `vmm`/`networking`/`clustermgmt` `Configuration` objects.
- `server.Context` — `from_env` defaults and overrides, the bare `KeyError` on a
  missing required variable (pinned as-is, not fixed), `state_str`.
- `ClusterMgmt.list_physical_gpu_profiles` and the GPU half of
  `vmm.provision_vm` — via the cached-client seam (see below).
- `VmProvisionRequest.__post_init__` GPU validation — the required triple,
  case-insensitive vendor, `PASSTHROUGH_*`-only modes (`VIRTUAL` rejected while
  vGPU is out of scope), and `gpu_count == 0` ignoring every other GPU field.
- Every `from_nutanix_*` converter plus the `vmm._disk_*` helpers. These build
  **real** SDK models: they construct empty, accept attribute assignment
  (UUID-validated `ext_id`s), and the converters use `isinstance` against
  concrete SDK classes that a stub could not satisfy. Stubs (`conftest.py`) are
  used only where a real object is impossible — see below.

## Not testable today

- **Most API-calling methods** (`list_vms`, `list_clusters`, `list_subnets`,
  `get_cluster_stats`, `get_vm_details`, `set_vm_power_state`, …). No
  constructor seam: `VirtualMachineMgmt.__init__` (and its `ClusterMgmt` /
  `Networking` siblings) builds `vmm.Configuration()` itself, and the `client` /
  `vms_api` / `tasks_api` properties construct `ApiClient` / `VmApi` by name.
  Clients cannot be injected, so covering these means patching module globals —
  heavy mocking that would test the patch, not the code.

  There is one usable seam, and the two GPU test files use it: each `*_api`
  property only builds a client when its cached `_*_api` attribute is absent,
  so assigning `mgmt._clusters_api` / `_vms_api` / `_tasks_api` swaps the API
  out with no patching. It reaches anything whose only other dependency is
  `paginate`, and `provision_vm` as long as the fake task succeeds on the first
  poll (otherwise the hard-coded `time.sleep(2)` below applies).
- **`vmm.provision_vm`'s task-polling loop.** Hard-codes
  `max_wait_seconds = 120` and `time.sleep(2)`, with no clock seam, so only the
  first-poll-succeeds path is reachable. The VM spec it builds *is* covered —
  see `test_vmm_provision_gpus.py`.
- **The FastAPI app and its routes.** `server.py:96-102` builds the `Context`
  and all three service objects inside `lifespan`, so a `TestClient` needs live
  `NUTANIX_*` credentials; there is no way to inject a `Context`.
- **Dead converter branches.** `net.Subnet` exposes only `cluster_reference`
  and its setter rejects non-UUID strings, so three of the four cluster-id
  lookups in `SubnetMetadata.from_nutanix_subnet` are unreachable with a real
  SDK object; they are stubbed and labelled.
