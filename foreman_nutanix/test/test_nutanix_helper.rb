# This calls the main test_helper in Foreman-core
require 'test_helper'

# Add plugin to FactoryBot's paths
FactoryBot.definition_file_paths << File.join(File.dirname(__FILE__), 'factories')
FactoryBot.reload

if ENV['VCR'] == '1'
  VCR.configure do |c|
    c.cassette_library_dir = ForemanNutanix::Engine.root.join('test', 'fixtures')
    c.hook_into :webmock
  end
end

class NutanixTestCase < ActiveSupport::TestCase
  let(:nutanix_access_token) { 'ya29.c.stubbed_token' }
  let(:gce_cr) { FactoryBot.create(:compute_resource, :nutanix_gce) }
  let(:nutanix_project_id) { gce_cr.nutanix_project_id }
  let(:gauth_json) { ((ENV['VCR'] == '1') ? ENV['GCE_AUTH'] : nil) || gce_cr.password }

  setup do
    ::Signet::OAuth2::Client.any_instance.stubs(fetch_access_token!: nutanix_access_token) unless ENV['VCR'] == '1'
  end
end
