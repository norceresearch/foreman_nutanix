# foreman_nutanix

Foreman plugin to create compute resource and (de)provision hosts using [Nutanix](https://www.nutanix.com/).

---

NOTE: This is a WIP and will not be shocking to find broken features, dead code, and generally not amazing Ruby code
specifically. First time writing Ruby... :)

---

### Install

The project layout includes a Python 'shim server'. This is because the official SDKs by Nutanix do not include Ruby,
and re-implementing an SDK wasn't appealing. It should make it easier to upgrade/change between Nutanix versions.

#### Shim Server

Until we publish via PyPI, one can install from source.
Assuming you can use [uv](https://github.com/astral-sh/uv), it'll look something like this:

```bash
uv pip install .
export NUTANIX_API_KEY=...someApiKey...
export NUTANIX_HOST=..some.host.com...
uv run fastapi run src/nutanix_shim_server/server.py
```

#### Foreman Plugin

Should be able to be installed as normal using path in the Gemfile, until we publish it as a Gem itself.

```bash
# Gemfile
gem 'foreman_nutanix', :path => '/path/to/repo/foreman_nutanix/foreman_nutanix'
```

And export `NUTANIX_SHIM_SERVER_ADDR=https://my-nutanix-host-addr`
