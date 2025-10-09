# Foreman Google

Foreman plugin for Google Compute Engine.

## Installation
```shell
foreman-installer --enable-foreman-plugin-google
```
Or see [Plugins documentation](https://www.theforeman.org/plugins/#2.Installation)
for how to install Foreman plugins

## Usage
* Create an account and project at [console.cloud.google.com](https://console.cloud.google.com)
* In _API & Services > Credentials_ create new service account (role: `Editor`) 
* On account detail page go to _Keys_ and create new `JSON` key 
* In Foreman, go to _Infrastructure > Compute Resources_ and create Compute Resource
```
name: <your-name>
provider: Google
Google Project ID: <your-project-id>
Client Email: service account's email
Certificate Path: JSON file
Zone: select the zone you want
```

## Contributing

See [Developer Guide](/docs/developer_guide.md), fork and send a pull request. Thanks!

## Copyright

Copyright (c) 2021 The Foreman Team

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
