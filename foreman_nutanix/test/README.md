# Tests

Standalone minitest. No Rails, no Foreman, no database, no `test/dummy`.

Run with:

```
bundle exec rake test
```

`test_helper.rb` requires only `lib/foreman_nutanix/shim_client.rb`, which is
deliberately plain Ruby (net/http, json, uri). That is the whole reason the
suite boots in milliseconds with nothing installed but minitest and rake.

## What this covers

`ForemanNutanix::ShimClient` — base URL resolution, trailing-slash chomping,
verb and path construction, JSON body encoding, `success?` / `no_content?` /
`code` / `body` / `json` on the response value object, and `normalize_uuid`.
HTTP is faked through the `http:` keyword seam; no network, no webmock.

## What cannot be tested here

Everything that needs a booted Foreman:

- `ForemanNutanix::Nutanix` — it is a `ComputeResource` subclass, and `cluster`
  is stored in the inherited `url` column, so instantiating it at all needs
  ActiveRecord, the Foreman schema, and the compute-resource STI machinery.
- `ForemanNutanix::HostManagedExtensions` — a concern mixed into `Host::Managed`.
- The `.erb` views under `app/views/`.
- The API controller extensions under `app/controllers/`.
- Anything touching the database, `Rails.logger`, or `Foreman::Plugin`.

`NutanixCompute` and `NutanixAdapter` are plain objects but still call
`Rails.logger` on nearly every method, so they are not reachable from here
either without stubbing Rails.

## What a full harness would need

1. A `test/dummy` Rails app generated against a Foreman core checkout.
2. That Foreman core pinned to a known version (the plugin requires >= 3.14.0),
   since plugin tests load Foreman's own `test_helper`.
3. A database created and migrated in CI before the suite runs.

Not built. The standalone suite above is the part that pays for itself today.
