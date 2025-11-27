require File.expand_path('lib/foreman_nutanix/version', __dir__)

Gem::Specification.new do |s|
  s.name        = 'foreman_nutanix'
  s.version     = ForemanNutanix::VERSION
  s.metadata    = { 'is_foreman_plugin' => 'true',
'rubygems_mfa_required' => 'true' }
  s.license     = 'GPL-3.0'
  s.authors     = ['The Foreman Team']
  s.email       = ['dev@community.theforeman.org']
  s.homepage    = 'https://github.com/norceresearch/foreman_nutanix'
  s.summary     = 'Nutanix plugin for Foreman'
  s.description = 'Nutanix compute resource plugin for Foreman'
  s.required_ruby_version = '>= 2.7', '< 4'

  s.files = Dir['{app,config,db,lib,locale,webpack}/**/*'] + ['LICENSE', 'Rakefile', 'README.md', 'package.json']
  s.test_files = Dir['test/**/*'] + Dir['webpack/**/__tests__/*.js']

  s.add_dependency 'foreman-tasks', '>=5.0'

  s.add_development_dependency 'rdoc'
  s.add_development_dependency 'theforeman-rubocop', '~> 0.1.1'
end
