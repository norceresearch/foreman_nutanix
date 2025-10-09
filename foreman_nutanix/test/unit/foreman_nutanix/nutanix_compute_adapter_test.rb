require 'test_google_helper'

require 'google/cloud/compute/v1/zones/credentials'
module ForemanGoogle
  class GoogleComputeAdapterTest < GoogleTestCase
    subject { ForemanGoogle::GoogleComputeAdapter.new(auth_json_string: gauth_json) }

    describe '#instance' do
      setup do
        stub_request(:get, 'https://compute.googleapis.com/compute/v1/projects/coastal-haven-123456/zones/us-east1-b/instances/instance-1')
          .to_return(body: File.read(File.join(__dir__, '..', '..', 'fixtures', 'instance.json')))
      end

      it 'gets instance by id' do
        instance = subject.instance('us-east1-b', 'instance-1')
        value(instance).must_be_kind_of(Google::Cloud::Compute::V1::Instance)
        value(instance.id).must_equal(123_456_789)
      end
    end

    describe '#instance - not found' do
      setup do
        stub_request(:get, 'https://compute.googleapis.com/compute/v1/projects/coastal-haven-123456/zones/us-east1-b/instances/not-existing-instance')
          .to_raise(Google::Cloud::NotFoundError)
      end

      it 'should raise an error' do
        value { subject.instance('us-east1-b', 'not-existing-instance') }.must_raise(ActiveRecord::RecordNotFound)
      end
    end

    describe '#instances' do
      setup do
        stub_request(:get, 'https://compute.googleapis.com/compute/v1/projects/coastal-haven-123456/zones/us-east1-b/instances')
          .to_return(body: File.read(File.join(__dir__, '..', '..', 'fixtures', 'instance_list.json')))
      end

      it 'gets instance by id' do
        instances = subject.instances('us-east1-b')
        value(instances[0]).must_be_kind_of(Google::Cloud::Compute::V1::Instance)
        value(instances[0].id).must_equal(123)
      end
    end

    describe '#zones' do
      setup do
        stub_request(:get, 'https://compute.googleapis.com/compute/v1/projects/coastal-haven-123456/zones')
          .to_return(body: File.read(File.join(__dir__, '..', '..', 'fixtures', 'zones.json')))
      end

      it 'show zones' do
        zones = subject.zones
        value(zones.first.name).must_be_kind_of(String)
        value(zones.first.description).must_be_kind_of(String)
      end
    end

    describe '#networks' do
      setup do
        stub_request(:get, 'https://compute.googleapis.com/compute/v1/projects/coastal-haven-123456/global/networks')
          .to_return(body: File.read(File.join(__dir__, '..', '..', 'fixtures', 'networks.json')))
      end

      it 'show networks' do
        assert_equal ['default'], subject.networks.map(&:name)
      end
    end

    describe '#machine_types' do
      setup do
        stub_request(:get, 'https://compute.googleapis.com/compute/v1/projects/coastal-haven-123456/zones/us-east1-b/machineTypes')
          .to_return(body: File.read(File.join(__dir__, '..', '..', 'fixtures', 'machine_types.json')))
      end

      it 'list machine_types' do
        assert_equal ['machine_type_001'], subject.machine_types('us-east1-b').map(&:name)
      end
    end

    describe '#images' do
      setup do
        stub_request(:get, 'https://compute.googleapis.com/compute/v1/projects/coastal-haven-123456/global/images')
          .to_return(body: File.read(File.join(__dir__, '..', '..', 'fixtures', 'images_coastal.json')))
      end

      it 'list images' do
        stub_request(:get, 'https://compute.googleapis.com/compute/v1/projects/centos-cloud/global/images')
          .to_return(body: File.read(File.join(__dir__, '..', '..', 'fixtures', 'images_centos_cloud.json')))

        subject.stub(:all_projects, %w[centos-cloud]) do
          assert_equal %w[coastal-image centos-6], subject.images.map(&:name)
        end
      end

      it 'list images with filter' do
        not_found_body = File.read(File.join(__dir__, '..', '..', 'fixtures', 'images_nothing_found.json'))
        %w[coastal-haven-123456 centos-cloud].each do |project|
          url = "https://compute.googleapis.com/compute/v1/projects/#{project}/global/images?filter=name%20=%20%22NOTHING_FOUND%22"
          stub_request(:get, url).to_return(body: not_found_body)
        end

        subject.stub(:all_projects, %w[centos-cloud]) do
          assert_empty subject.images(filter: 'name = "NOTHING_FOUND"')
        end
      end

      it 'ignore deprecated images' do
        stub_request(:get, 'https://compute.googleapis.com/compute/v1/projects/deprecated/global/images')
          .to_return(body: File.read(File.join(__dir__, '..', '..', 'fixtures', 'images_deprecated.json')))

        subject.stub(:all_projects, %w[deprecated]) do
          assert_equal ['coastal-image'], subject.images.map(&:name)
        end
      end
    end

    describe 'manage vm' do
      it '#insert' do
        stub_request(:post, 'https://compute.googleapis.com/compute/v1/projects/coastal-haven-123456/zones/us-east1-b/instances')
          .to_return(status: 200, body: File.read(File.join(__dir__, '..', '..', 'fixtures', 'instance_insert.json')))

        stub_request(:get, 'https://compute.googleapis.com/compute/v1/projects/coastal-haven-123456/zones/us-east1-b/operations/6200725776819157246')
          .to_return(status: 200, body: File.read(File.join(__dir__, '..', '..', 'fixtures', 'operation_get.json')))

        args = {
          name: 'foreman-test',
          machine_type: 'zones/us-east1-b/machineTypes/e2-micro',
          disks: [{ source: 'zones/us-east1-b/disks/foreman-test-disk1', boot: true }],
          network_interfaces: [{ network: 'global/networks/default' }],
        }

        result = subject.insert_instance('us-east1-b', args)

        assert 'insert', result.operation.operation_type
        assert_includes result.operation.target_link, 'foreman-test-google'
      end

      it '#insert with error' do
        stub_request(:post, 'https://compute.googleapis.com/compute/v1/projects/coastal-haven-123456/zones/us-east1-b/instances')
          .to_return(status: 200, body: File.read(File.join(__dir__, '..', '..', 'fixtures', 'instance_insert.json')))

        stub_request(:get, 'https://compute.googleapis.com/compute/v1/projects/coastal-haven-123456/zones/us-east1-b/operations/6200725776819157246')
          .to_return(status: 200, body: File.read(File.join(__dir__, '..', '..', 'fixtures', 'operation_error.json')))

        args = {
          name: 'foreman-test',
          machine_type: 'zones/us-east1-b/machineTypes/e2-micro',
          disks: [{ source: 'zones/us-east1-b/disks/foreman-test-disk1', boot: true }],
          network_interfaces: [{ network: 'global/networks/default' }],
        }

        value { subject.insert_instance('us-east1-b', args) }.must_raise(::Google::Cloud::Error)
      end

      it '#start' do
        stub_request(:post, 'https://compute.googleapis.com/compute/v1/projects/coastal-haven-123456/zones/us-east1-b/instances/instance_name/start')
          .to_return(status: 200, body: File.read(File.join(__dir__, '..', '..', 'fixtures', 'instance_start.json')))
        result = subject.start('us-east1-b', 'instance_name')
        assert 'start', result.operation.operation_type
      end

      it '#stop' do
        stub_request(:post, 'https://compute.googleapis.com/compute/v1/projects/coastal-haven-123456/zones/us-east1-b/instances/instance_name/stop')
          .to_return(status: 200, body: File.read(File.join(__dir__, '..', '..', 'fixtures', 'instance_stop.json')))
        result = subject.stop('us-east1-b', 'instance_name')
        assert 'stop', result.operation.operation_type
      end

      it '#set_disk_auto_delete' do
        stub_request(:get, 'https://compute.googleapis.com/compute/v1/projects/coastal-haven-123456/zones/us-east1-b/instances/instance_name')
          .to_return(body: File.read(File.join(__dir__, '..', '..', 'fixtures', 'instance.json')))

        stub_request(:post, 'https://compute.googleapis.com/compute/v1/projects/coastal-haven-123456/zones/us-east1-b/instances/instance_name/setDiskAutoDelete?autoDelete=true&deviceName=instance-1')
          .to_return(status: 200, body: File.read(File.join(__dir__, '..', '..', 'fixtures', 'instance_set_disk_auto_delete.json')))
        result = subject.set_disk_auto_delete('us-east1-b', 'instance_name')

        assert 'device-1', result[0].source
        assert result[0].auto_delete
      end
    end

    describe 'disks' do
      it '#insert' do
        stub_request(:post, 'https://compute.googleapis.com/compute/v1/projects/coastal-haven-123456/zones/us-east1-b/disks')
          .to_return(status: 200, body: File.read(File.join(__dir__, '..', '..', 'fixtures', 'disks_insert.json')))

        result = subject.insert_disk('us-east1-b', { name: 'foreman-disk1', size_gb: 23 })
        assert_includes result.operation.target_link, 'foreman-disk1'
        assert 'insert', result.operation.operation_type
      end

      it '#get' do
        stub_request(:get, 'https://compute.googleapis.com/compute/v1/projects/coastal-haven-123456/zones/us-east1-b/disks/foreman-disk1')
          .to_return(status: 200, body: File.read(File.join(__dir__, '..', '..', 'fixtures', 'disks_get.json')))
        result = subject.disk('us-east1-b', 'foreman-disk1')
        assert 'foreman-disk1', result.name
      end

      it '#delete' do
        stub_request(:delete, 'https://compute.googleapis.com/compute/v1/projects/coastal-haven-123456/zones/us-east1-b/disks/foreman-disk1')
          .to_return(status: 200, body: File.read(File.join(__dir__, '..', '..', 'fixtures', 'disks_delete.json')))
        result = subject.delete_disk('us-east1-b', 'foreman-disk1')

        assert_includes result.operation.target_link, 'foreman-disk1'
        assert 'delete', result.operation.operation_type
      end
    end
  end
end
