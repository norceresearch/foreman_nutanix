# Foreman Nutanix Plugin

Nutanix compute resource plugin for [Foreman](https://theforeman.org/).

## Installation

Add to your Foreman's bundler.d:

```ruby
# bundler.d/foreman_nutanix.rb
gem 'foreman_nutanix'
```

Then run:

```bash
bundle install
```

## Configuration

This plugin requires the [nutanix-shim-server](https://pypi.org/project/nutanix-shim-server/) to be running and accessible.

Set the shim server address:

```bash
export NUTANIX_SHIM_SERVER_ADDR=http://localhost:8000
```

## License

MIT
