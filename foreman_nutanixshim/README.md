# ForemanNutanixshim

Initial Nutanix support for Foreman.

First attempt will likely include offloading actual provisioning to the Django app so we can
make use of the official Nutanix Python SDK rather than doing all that logic in Ruby.

## Installation

See [How_to_Install_a_Plugin](http://projects.theforeman.org/projects/foreman/wiki/How_to_Install_a_Plugin)
for how to install Foreman plugins

## Usage

Add to foreman by adding the following to the Gemfile:

```
gem 'foreman_nutanixshim', path: '../foreman-norce/plugins/foreman_nutanixshim'
```

## TODO

- [x] Basic rendering of 'Nutanix' compute resource
- [] Configure the Nutanix shim / Django server endpoint
- [] Dynamic listing of available Nutanix clusters from Django app
- [] Successfully provision something...

## Contributing

Fork and send a Pull Request. Thanks!

### Helpful links

Reference implementation that's helpful:
- Kubevirt
  - https://github.com/theforeman/foreman_kubevirt
  - [kubevirt.rb model](https://github.com/theforeman/foreman_kubevirt/blob/master/app/models/foreman_kubevirt/kubevirt.rb)
  - [engine.rb](https://github.com/theforeman/foreman_kubevirt/blob/master/lib/foreman_kubevirt/engine.rb)

## Copyright

Copyright (c) 2025 NORCE Research

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

