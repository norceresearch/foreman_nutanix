# foreman_nutanix

[![Nutanix Shim Server CI](https://github.com/norceresearch/foreman_nutanix/actions/workflows/ci.yml/badge.svg)](https://github.com/norceresearch/foreman_nutanix/actions/workflows/ci.yml)
[![Gem Version](https://badge.fury.io/rb/foreman_nutanix.svg?icon=si%3Arubygems)](https://badge.fury.io/rb/foreman_nutanix)
![PyPI - Version](https://img.shields.io/pypi/v/nutanix-shim-server)

Foreman plugin to create compute resource and (de)provision hosts using [Nutanix](https://www.nutanix.com/).

---

_NOTE: This is a WIP and will not be shocking to find broken features, dead code,
and probably not the best Ruby coding you've ever seen._

---

### Install

The project layout includes a Python 'shim server'. This is because the official SDKs by Nutanix do not include Ruby,
and re-implementing an SDK wasn't appealing. It should make it easier to upgrade/change between Nutanix versions.

#### Shim Server

Requires these env vars set:

```bash
export NUTANIX_API_KEY=...someApiKey...
export NUTANIX_HOST=..some.host.com...
```

###### From PyPI

<https://pypi.org/project/nutanix-shim-server/>

```
pip install nutanix-shim-server
nutanix-shim-server --port 8000
```

###### From source

Assuming you can use [uv](https://github.com/astral-sh/uv), it'll look something like this:

```bash
uv pip install .
uv run nutanix-shim-server --port 8000
```

###### Serving with https

By default, using `nutanix-shim-server` will use the production server of `fastapi` and all (if any)
additional options will be supplied to `fastapi`.

If you want SSL/https, then supply `--ssl-certfile` and `--ssl-keyfile`, it will then
use `uvicorn` with https, all following options will be supplied to `uvicorn` instead.

---

#### Foreman Plugin

Requires this env var set:

```bash
export NUTANIX_SHIM_SERVER_ADDR=https://nutanix-shim-server-addr
```

###### From Ruby Gems

<https://rubygems.org/gems/foreman_nutanix>

```ruby
gem 'foreman_nutanix'
```

###### From Source

```ruby
# Gemfile
gem 'foreman_nutanix', :path => '/path/to/repo/foreman_nutanix/foreman_nutanix'
```
