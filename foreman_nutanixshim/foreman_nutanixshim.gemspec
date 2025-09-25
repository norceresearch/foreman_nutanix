require File.expand_path('lib/foreman_nutanixshim/version', __dir__)

Gem::Specification.new do |s|
  s.name        = 'foreman_nutanixshim'
  s.version     = ForemanNutanixshim::VERSION
  s.metadata    = { 'is_foreman_plugin' => 'true' }
  s.license     = 'GPL-3.0'
  s.authors     = ['Miles Granger']
  s.email       = ['mgra@norceresearch.no']
  s.homepage    = 'https://gitlab.intra.norceresearch.no/norce-it/foreman'
  s.summary     = 'Foreman plugin shim to interface with Nutanix'
  # also update locale/gemspec.rb
  s.description = 'Foreman plugin shim to interface with Nutanix'

  s.files = Dir['{app,config,db,lib,locale,webpack}/**/*'] + ['LICENSE', 'Rakefile', 'README.md', 'package.json']
  s.test_files = Dir['test/**/*'] + Dir['webpack/**/__tests__/*.js']

  s.required_ruby_version = '>= 2.7', '< 4'

  s.add_development_dependency 'rdoc'
end
