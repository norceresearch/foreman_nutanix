require File.expand_path('lib/foreman_nutanix/version', __dir__)

Gem::Specification.new do |s|
  s.name        = 'foreman_nutanix'
  s.version     = ForemanNutanix::VERSION
  s.metadata    = { 'is_foreman_plugin' => 'true',
'rubygems_mfa_required' => 'true' }
  s.license     = 'GPL-3.0'
  s.authors     = ['The Foreman Team']
  s.email       = ['dev@community.theforeman.org']
  s.homepage    = 'https://gitlab.intra.norceresearch.no/norce-it/foreman'
  s.summary     = 'nutanix Compute Engine plugin for the Foreman'
  s.description = 'nutanix Compute Engine plugin for the Foreman'
  s.required_ruby_version = '>= 2.7', '< 4'

  s.files = Dir['{app,config,db,lib,locale,webpack}/**/*'] + ['LICENSE', 'Rakefile', 'README.md', 'package.json']
  s.test_files = Dir['test/**/*'] + Dir['webpack/**/__tests__/*.js']

  # Pin nutanix versions to avoid breaking changes
  # Never versions with nutanix-protobuf > 3.25.4
  # are failing with `undefined method 'build'` error
  s.add_dependency 'google-apis-compute_v1', '0.54.0'
  s.add_dependency 'google-cloud-compute', '0.5.0'
  s.add_dependency 'google-protobuf', '3.24.3'

  s.add_development_dependency 'rdoc'
  s.add_development_dependency 'theforeman-rubocop', '~> 0.1.1'
end
